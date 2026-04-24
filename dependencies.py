from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from security import decode_token, verify_api_key
from redis import rate_limit_check
from config import settings
from models import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    token = credentials.credentials

    # Support API key auth
    if token.startswith("aiv_"):
        from sqlalchemy import select
        from app.auth.models import User as UserModel
        users = await db.scalars(select(UserModel).where(UserModel.api_key_prefix == token[:10]))
        for u in users:
            if u.api_key_hash and verify_api_key(token, u.api_key_hash):
                return u
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

    # JWT auth
    payload = decode_token(token)
    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


async def require_verified(user: User = Depends(get_current_user)) -> User:
    if not user.is_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Email not verified")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


def require_plan(*plans: str):
    """Dependency factory: require_plan('starter', 'pro', 'agency')"""
    async def _check(user: User = Depends(require_verified)) -> User:
        if user.plan not in plans and user.role != UserRole.ADMIN:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                f"This feature requires one of: {', '.join(plans)} plan",
            )
        return user
    return _check


async def check_rate_limit(user: User = Depends(get_current_user)) -> User:
    key = f"rate:{user.id}:minute"
    allowed = await rate_limit_check(key, settings.RATE_LIMIT_PER_MINUTE, window=60)
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
    return user
