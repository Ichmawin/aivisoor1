import logging
import time
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from config import settings
from app.core.database import init_db
from app.auth.router import router as auth_router
from app.subscriptions.router import router as sub_router
from app.reports.service import router as reports_router
from app.projects.router import router as projects_router
from app.admin.router import router as admin_router

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Sentry ────────────────────────────────────────────────────────────────────

if settings.SENTRY_DSN and settings.is_production:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.2,
        environment=settings.APP_ENV,
    )


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    yield
    logger.info("Shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


@app.middleware("http")
async def request_timer(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Response-Time"] = f"{duration}ms"
    response.headers["X-App-Version"] = settings.APP_VERSION
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")
    return response


# ── Error handlers ────────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(l) for l in e["loc"]), "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

PREFIX = "/api/v1"
app.include_router(auth_router, prefix=PREFIX)
app.include_router(sub_router, prefix=PREFIX)
app.include_router(reports_router, prefix=PREFIX)
app.include_router(projects_router, prefix=PREFIX)
app.include_router(admin_router, prefix=PREFIX)


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION, "env": settings.APP_ENV}
