import secrets
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.auth.models import User
from app.auth.schemas import UserRegister, UserUpdate, PasswordChange
from app.core.security import (
    hash_password, verify_password, validate_password_strength,
    create_access_token, create_refresh_token, decode_token,
    generate_2fa_secret, generate_2fa_qr, verify_2fa_code, generate_api_key,
)
from app.core.email import send_email
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class AuthService:

    # ── Registration ──────────────────────────────────────────────────────────

    async def register(self, db: AsyncSession, data: UserRegister) -> User:
        # Check duplicate
        existing = await db.scalar(select(User).where(User.email == data.email))
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

        validate_password_strength(data.password)

        token = secrets.token_urlsafe(32)
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            verification_token=token,
        )
        db.add(user)
        await db.flush()

        await send_email(user.email, "welcome", {
            "name": user.full_name,
            "dashboard_url": f"https://app.aivisoor.com/verify?token={token}",
        })

        logger.info(f"New user registered: {user.email}")
        return user

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(
        self, db: AsyncSession, email: str, password: str, totp_code: str | None
    ) -> tuple[str, str, User]:
        user = await db.scalar(select(User).where(User.email == email))
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")

        # 2FA check
        if user.totp_enabled:
            if not totp_code:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "2FA code required")
            if not verify_2fa_code(user.totp_secret, totp_code):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid 2FA code")

        extra = {"role": user.role, "plan": user.plan}
        access = create_access_token(str(user.id), extra)
        refresh = create_refresh_token(str(user.id))
        return access, refresh, user

    # ── Token refresh ─────────────────────────────────────────────────────────

    async def refresh_tokens(
        self, db: AsyncSession, refresh_token: str
    ) -> tuple[str, str]:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = await self._get_user_or_404(db, payload["sub"])
        extra = {"role": user.role, "plan": user.plan}
        return create_access_token(str(user.id), extra), create_refresh_token(str(user.id))

    # ── Email verification ────────────────────────────────────────────────────

    async def verify_email(self, db: AsyncSession, token: str) -> None:
        user = await db.scalar(select(User).where(User.verification_token == token))
        if not user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid verification token")
        user.is_verified = True
        user.verification_token = None

    # ── Password reset ────────────────────────────────────────────────────────

    async def request_password_reset(self, db: AsyncSession, email: str) -> None:
        user = await db.scalar(select(User).where(User.email == email))
        if not user:
            return  # Silent — don't expose email existence
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        await send_email(email, "password_reset", {
            "reset_url": f"https://app.aivisoor.com/reset-password?token={token}",
        })

    async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> None:
        user = await db.scalar(select(User).where(User.reset_token == token))
        if not user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid reset token")
        validate_password_strength(new_password)
        user.hashed_password = hash_password(new_password)
        user.reset_token = None

    # ── Profile ───────────────────────────────────────────────────────────────

    async def update_profile(
        self, db: AsyncSession, user: User, data: UserUpdate
    ) -> User:
        if data.full_name:
            user.full_name = data.full_name
        if data.email and data.email != user.email:
            existing = await db.scalar(select(User).where(User.email == data.email))
            if existing:
                raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")
            user.email = data.email
            user.is_verified = False
        return user

    async def change_password(
        self, db: AsyncSession, user: User, data: PasswordChange
    ) -> None:
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is wrong")
        validate_password_strength(data.new_password)
        user.hashed_password = hash_password(data.new_password)

    # ── 2FA ───────────────────────────────────────────────────────────────────

    async def setup_2fa(self, db: AsyncSession, user: User) -> dict:
        secret = generate_2fa_secret()
        user.totp_secret = secret
        qr = generate_2fa_qr(secret, user.email)
        return {"qr_code": qr, "secret": secret}

    async def enable_2fa(self, db: AsyncSession, user: User, code: str) -> None:
        if not user.totp_secret:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Setup 2FA first")
        if not verify_2fa_code(user.totp_secret, code):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid code")
        user.totp_enabled = True

    async def disable_2fa(self, db: AsyncSession, user: User, code: str) -> None:
        if not verify_2fa_code(user.totp_secret, code):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid code")
        user.totp_enabled = False
        user.totp_secret = None

    # ── API Keys ──────────────────────────────────────────────────────────────

    async def generate_api_key(self, db: AsyncSession, user: User) -> str:
        raw, hashed = generate_api_key()
        user.api_key_hash = hashed
        user.api_key_prefix = raw[:10]
        return raw

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_user_or_404(self, db: AsyncSession, user_id: str) -> User:
        user = await db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        return user


auth_service = AuthService()
