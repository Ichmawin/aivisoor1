import uuid
from sqlalchemy import String, Boolean, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.USER)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 2FA
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # API Key (hashed)
    api_key_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_key_prefix: Mapped[str | None] = mapped_column(String(12), nullable=True)

    # Relations
    subscription: Mapped["Subscription"] = relationship(  # noqa: F821
        "Subscription", back_populates="user", uselist=False, lazy="selectin"
    )
    projects: Mapped[list["Project"]] = relationship(  # noqa: F821
        "Project", back_populates="owner", lazy="selectin"
    )

    @property
    def plan(self) -> str:
        if self.subscription and self.subscription.is_active:
            return self.subscription.plan
        return "free"

    def __repr__(self) -> str:
        return f"<User {self.email}>"
