from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "AIVisoor"
    APP_ENV: str = "production"
    APP_VERSION: str = "1.0.0"
    APP_SECRET_KEY: str
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 30

    # AI Providers
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"
    PERPLEXITY_API_KEY: str
    PERPLEXITY_MODEL: str = "sonar-pro"

    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PRICE_STARTER: str
    STRIPE_PRICE_PRO: str
    STRIPE_PRICE_AGENCY: str

    # Email (Resend)
    RESEND_API_KEY: str
    EMAIL_FROM: str = "noreply@aivisoor.com"
    EMAIL_FROM_NAME: str = "AIVisoor"

    # Storage (S3-compatible)
    S3_ENDPOINT: str = ""
    S3_BUCKET: str = "aivisoor"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "eu-central-1"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Plan limits
    PLAN_FREE_REPORTS: int = 1
    PLAN_STARTER_REPORTS: int = 10
    PLAN_PRO_REPORTS: int = 50
    PLAN_AGENCY_REPORTS: int = 999999

    # Sentry
    SENTRY_DSN: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def plan_limits(self) -> dict:
        return {
            "free": self.PLAN_FREE_REPORTS,
            "starter": self.PLAN_STARTER_REPORTS,
            "pro": self.PLAN_PRO_REPORTS,
            "agency": self.PLAN_AGENCY_REPORTS,
        }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
