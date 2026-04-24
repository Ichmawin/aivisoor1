from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import secrets
import pyotp
import qrcode
import io
import base64

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def validate_password_strength(password: str) -> None:
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not any(c.isupper() for c in password):
        errors.append("one uppercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("one digit")
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must contain: {', '.join(errors)}",
        )


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(subject: str, extra: dict = {}) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire, "type": "access", **extra}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_EXPIRE_DAYS
    )
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── 2FA (TOTP) ────────────────────────────────────────────────────────────────

def generate_2fa_secret() -> str:
    return pyotp.random_base32()


def get_2fa_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email, issuer_name=settings.APP_NAME
    )


def generate_2fa_qr(secret: str, email: str) -> str:
    """Returns base64-encoded QR code PNG."""
    uri = get_2fa_uri(secret, email)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def verify_2fa_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ── API Keys ──────────────────────────────────────────────────────────────────

def generate_api_key() -> tuple[str, str]:
    """Returns (raw_key, hashed_key). Store only the hash."""
    raw = f"aiv_{secrets.token_urlsafe(32)}"
    hashed = hash_password(raw)
    return raw, hashed


def verify_api_key(raw: str, hashed: str) -> bool:
    return verify_password(raw, hashed)
