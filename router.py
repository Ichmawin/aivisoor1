from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_verified
from app.auth.models import User
from app.subscriptions.stripe_service import stripe_service
from app.subscriptions.models import PLAN_METADATA

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str = "https://app.aivisoor.com/settings/billing?success=1"
    cancel_url: str = "https://app.aivisoor.com/settings/billing"


class PortalRequest(BaseModel):
    return_url: str = "https://app.aivisoor.com/settings/billing"


@router.get("/plans")
async def get_plans():
    return {"plans": PLAN_METADATA}


@router.get("/me")
async def get_my_subscription(user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.subscriptions.models import Subscription
    sub = await db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    if not sub:
        return {"plan": "free", "reports_used": 0, "reports_limit": 1, "is_active": True}
    return {
        "plan": sub.plan,
        "reports_used": sub.reports_used,
        "reports_limit": sub.reports_limit,
        "usage_percent": sub.usage_percent,
        "is_active": sub.is_active,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "current_period_end": sub.current_period_end,
    }


@router.post("/checkout")
async def create_checkout(
    data: CheckoutRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    url = await stripe_service.create_checkout_session(
        db, user, data.plan, data.success_url, data.cancel_url
    )
    return {"checkout_url": url}


@router.post("/portal")
async def customer_portal(
    data: PortalRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    url = await stripe_service.create_portal_session(db, user, data.return_url)
    return {"portal_url": url}


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    await stripe_service.handle_webhook(db, payload, stripe_signature)
    return {"status": "ok"}
