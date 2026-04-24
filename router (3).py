from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.schemas import (
    UserRegister, UserLogin, TokenResponse, RefreshRequest,
    UserOut, UserUpdate, PasswordChange, PasswordResetRequest,
    PasswordReset, TwoFASetup, TwoFAVerify, APIKeyOut,
)
from app.auth.service import auth_service
from app.auth.dependencies import get_current_user, require_verified
from app.auth.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    return await auth_service.register(db, data)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    access, refresh, user = await auth_service.login(
        db, data.email, data.password, data.totp_code
    )
    return {"access_token": access, "refresh_token": refresh, "user": user}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    access, refresh = await auth_service.refresh_tokens(db, data.refresh_token)
    return {"access_token": access, "refresh_token": refresh}


@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    await auth_service.verify_email(db, token)
    return {"message": "Email verified successfully"}


@router.post("/password/reset-request")
async def request_reset(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.request_password_reset(db, data.email)
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/password/reset")
async def reset_password(data: PasswordReset, db: AsyncSession = Depends(get_db)):
    await auth_service.reset_password(db, data.token, data.new_password)
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.update_profile(db, user, data)


@router.post("/me/password")
async def change_password(
    data: PasswordChange,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.change_password(db, user, data)
    return {"message": "Password updated"}


@router.post("/2fa/setup", response_model=TwoFASetup)
async def setup_2fa(user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await auth_service.setup_2fa(db, user)


@router.post("/2fa/enable")
async def enable_2fa(
    data: TwoFAVerify,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.enable_2fa(db, user, data.code)
    return {"message": "2FA enabled"}


@router.post("/2fa/disable")
async def disable_2fa(
    data: TwoFAVerify,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.disable_2fa(db, user, data.code)
    return {"message": "2FA disabled"}


@router.post("/api-key", response_model=APIKeyOut)
async def generate_api_key(
    user: User = Depends(require_plan("pro", "agency")),
    db: AsyncSession = Depends(get_db),
):
    from app.auth.dependencies import require_plan
    raw = await auth_service.generate_api_key(db, user)
    from datetime import datetime, timezone
    return {"key": raw, "prefix": raw[:10], "created_at": datetime.now(timezone.utc)}
