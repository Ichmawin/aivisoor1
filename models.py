import uuid
import enum
from sqlalchemy import String, Boolean, Enum as SAEnum, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from app.core.database import Base


class PlanName(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    AGENCY = "agency"


PLAN_METADATA = {
    "free":    {"name": "Free",    "price": 0,   "reports": 1,      "features": ["1 report/month", "Basic scoring"]},
    "starter": {"name": "Starter", "price": 29,  "reports": 10,     "features": ["10 reports/month", "PDF export", "Email alerts"]},
    "pro":     {"name": "Pro",     "price": 79,  "reports": 50,     "features": ["50 reports/month", "API access", "Competitor tracking", "Priority support"]},
    "agency":  {"name": "Agency",  "price": 199, "reports": 999999, "features": ["Unlimited reports", "White-label", "Team seats", "Dedicated support"]},
}


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)

    plan: Mapped[PlanName] = mapped_column(SAEnum(PlanName), default=PlanName.FREE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Stripe
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Period
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)

    # Usage (resets monthly)
    reports_used: Mapped[int] = mapped_column(Integer, default=0)
    reports_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="subscription")  # noqa: F821

    @property
    def reports_limit(self) -> int:
        return PLAN_METADATA[self.plan]["reports"]

    @property
    def can_generate_report(self) -> bool:
        return self.reports_used < self.reports_limit

    @property
    def usage_percent(self) -> float:
        if self.reports_limit >= 999999:
            return 0.0
        return round((self.reports_used / self.reports_limit) * 100, 1)
