import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from datetime import datetime, timezone

from config import settings
from models import User
from subscriptions.models import Subscription, PlanName, PLAN_METADATA
from email import send_email
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

PRICE_TO_PLAN = {
    settings.STRIPE_PRICE_STARTER: PlanName.STARTER,
    settings.STRIPE_PRICE_PRO: PlanName.PRO,
    settings.STRIPE_PRICE_AGENCY: PlanName.AGENCY,
}


class StripeService:

    async def get_or_create_customer(self, db: AsyncSession, user: User) -> str:
        sub = await self._get_subscription(db, user)
        if sub.stripe_customer_id:
            return sub.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": str(user.id)},
        )
        sub.stripe_customer_id = customer.id
        return customer.id

    async def create_checkout_session(
        self, db: AsyncSession, user: User, plan: str, success_url: str, cancel_url: str
    ) -> str:
        price_map = {
            "starter": settings.STRIPE_PRICE_STARTER,
            "pro": settings.STRIPE_PRICE_PRO,
            "agency": settings.STRIPE_PRICE_AGENCY,
        }
        price_id = price_map.get(plan)
        if not price_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid plan")

        customer_id = await self.get_or_create_customer(db, user)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"user_id": str(user.id), "plan": plan},
            subscription_data={
                "trial_period_days": 7,
                "metadata": {"user_id": str(user.id)},
            },
        )
        return session.url

    async def create_portal_session(self, db: AsyncSession, user: User, return_url: str) -> str:
        customer_id = await self.get_or_create_customer(db, user)
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    async def handle_webhook(self, db: AsyncSession, payload: bytes, sig: str) -> None:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid signature")

        handlers = {
            "checkout.session.completed": self._on_checkout_completed,
            "customer.subscription.updated": self._on_subscription_updated,
            "customer.subscription.deleted": self._on_subscription_deleted,
            "invoice.payment_failed": self._on_payment_failed,
        }

        handler = handlers.get(event["type"])
        if handler:
            await handler(db, event["data"]["object"])
            logger.info(f"Webhook handled: {event['type']}")

    # ── Webhook handlers ──────────────────────────────────────────────────────

    async def _on_checkout_completed(self, db: AsyncSession, obj: dict) -> None:
        user_id = obj["metadata"]["user_id"]
        plan = obj["metadata"]["plan"]
        stripe_sub_id = obj.get("subscription")

        stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
        price_id = stripe_sub["items"]["data"][0]["price"]["id"]

        sub = await db.scalar(select(Subscription).where(Subscription.user_id == user_id))
        if not sub:
            return

        sub.plan = PRICE_TO_PLAN.get(price_id, PlanName.FREE)
        sub.stripe_subscription_id = stripe_sub_id
        sub.stripe_price_id = price_id
        sub.is_active = True
        sub.current_period_start = datetime.fromtimestamp(stripe_sub["current_period_start"], tz=timezone.utc)
        sub.current_period_end = datetime.fromtimestamp(stripe_sub["current_period_end"], tz=timezone.utc)

        user = await db.get(User, user_id)
        if user:
            await send_email(user.email, "subscription_upgraded", {
                "plan": plan,
                "reports_limit": PLAN_METADATA[plan]["reports"],
            })

    async def _on_subscription_updated(self, db: AsyncSession, obj: dict) -> None:
        sub = await db.scalar(
            select(Subscription).where(Subscription.stripe_subscription_id == obj["id"])
        )
        if not sub:
            return

        price_id = obj["items"]["data"][0]["price"]["id"]
        sub.plan = PRICE_TO_PLAN.get(price_id, PlanName.FREE)
        sub.is_active = obj["status"] in ("active", "trialing")
        sub.cancel_at_period_end = obj.get("cancel_at_period_end", False)
        sub.current_period_end = datetime.fromtimestamp(obj["current_period_end"], tz=timezone.utc)

    async def _on_subscription_deleted(self, db: AsyncSession, obj: dict) -> None:
        sub = await db.scalar(
            select(Subscription).where(Subscription.stripe_subscription_id == obj["id"])
        )
        if sub:
            sub.plan = PlanName.FREE
            sub.is_active = True  # Downgrade to free, don't deactivate
            sub.stripe_subscription_id = None

    async def _on_payment_failed(self, db: AsyncSession, obj: dict) -> None:
        customer_id = obj.get("customer")
        sub = await db.scalar(
            select(Subscription).where(Subscription.stripe_customer_id == customer_id)
        )
        if sub:
            user = await db.get(User, sub.user_id)
            if user:
                logger.warning(f"Payment failed for user {user.email}")

    # ── Usage tracking ────────────────────────────────────────────────────────

    async def increment_usage(self, db: AsyncSession, user: User) -> None:
        sub = await self._get_subscription(db, user)
        if not sub.can_generate_report:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                f"Monthly report limit reached ({sub.reports_limit}). Please upgrade.",
            )
        sub.reports_used += 1

    async def _get_subscription(self, db: AsyncSession, user: User) -> Subscription:
        sub = await db.scalar(select(Subscription).where(Subscription.user_id == user.id))
        if not sub:
            sub = Subscription(user_id=user.id)
            db.add(sub)
            await db.flush()
        return sub


stripe_service = StripeService()
