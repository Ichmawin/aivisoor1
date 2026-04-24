import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException, status, APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel

from app.reports.models import Report, ReportStatus
from app.auth.models import User
from app.auth.dependencies import get_current_user, require_verified, check_rate_limit
from app.subscriptions.stripe_service import stripe_service
from app.ai_engine.providers import run_ai_analysis
from app.core.database import get_db
from app.core.redis import cache_get, cache_set
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    domain: str
    niche: str | None = None
    project_id: str | None = None


class ReportOut(BaseModel):
    id: str
    domain: str
    niche: str | None
    status: str
    score_overall: int | None
    score_visibility: int | None
    score_authority: int | None
    score_coverage: int | None
    top_competitors: list | None
    recommendations: list | None
    pdf_url: str | None
    created_at: str

    class Config:
        from_attributes = True


# ── Background task ───────────────────────────────────────────────────────────

async def _run_report(report_id: str, domain: str, niche: str | None) -> None:
    """Runs in background — fetches AI data, scores, saves result."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        report = await db.get(Report, report_id)
        if not report:
            return
        try:
            report.status = ReportStatus.RUNNING
            await db.commit()

            analysis = await run_ai_analysis(domain, niche)
            scores = analysis["scores"]
            recommendations = _generate_recommendations(analysis)

            report.status = ReportStatus.DONE
            report.score_overall = scores["overall"]
            report.score_visibility = scores["visibility"]
            report.score_authority = scores["authority"]
            report.score_coverage = scores["coverage"]
            report.top_competitors = analysis["top_competitors"]
            report.recommendations = recommendations
            report.raw_data = {
                "queries_run": analysis["queries_run"],
                "mention_count": analysis["mention_count"],
                "total_responses": analysis["total_responses"],
            }

            await db.commit()

            # Notify user by email
            user = await db.get(User, report.user_id)
            if user:
                from app.core.email import send_email
                await send_email(user.email, "report_ready", {
                    "domain": domain,
                    "score": scores["overall"],
                    "report_url": f"https://app.aivisoor.com/reports/{report_id}",
                })

            logger.info(f"Report {report_id} completed. Score: {scores['overall']}")

        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            await db.commit()
            logger.error(f"Report {report_id} failed: {e}")


def _generate_recommendations(analysis: dict) -> list[dict]:
    """Generate actionable recommendations based on analysis."""
    recs = []
    scores = analysis["scores"]

    if scores["visibility"] < 30:
        recs.append({
            "priority": "high",
            "title": "Improve AI Discoverability",
            "description": "Your domain is rarely mentioned in AI answers. Create comprehensive FAQ pages and structured content that AI models can easily reference.",
        })
    if scores["authority"] < 40:
        recs.append({
            "priority": "high",
            "title": "Build Topical Authority",
            "description": "When mentioned, your brand isn't in a strong position. Publish in-depth guides and get cited by authoritative sources.",
        })
    if scores["coverage"] < 50:
        recs.append({
            "priority": "medium",
            "title": "Expand Content Coverage",
            "description": "Your content doesn't cover enough query types. Map out common questions in your niche and create dedicated content for each.",
        })
    if analysis["top_competitors"]:
        top = analysis["top_competitors"][0]["name"]
        recs.append({
            "priority": "medium",
            "title": f"Analyze Competitor: {top}",
            "description": f"{top} is frequently mentioned alongside your domain. Study their content strategy to understand why AI models prefer them.",
        })
    if scores["overall"] >= 70:
        recs.append({
            "priority": "low",
            "title": "Maintain Your Position",
            "description": "Your AI visibility is strong. Keep publishing quality content and monitor for changes in AI model behavior.",
        })

    return recs


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=ReportOut, status_code=status.HTTP_202_ACCEPTED)
async def create_report(
    data: ReportCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(check_rate_limit),
    db: AsyncSession = Depends(get_db),
):
    # Check usage limit
    await stripe_service.increment_usage(db, user)

    # Normalize domain
    domain = data.domain.lower().strip().replace("https://", "").replace("http://", "").rstrip("/")

    report = Report(
        user_id=user.id,
        domain=domain,
        niche=data.niche,
        project_id=uuid.UUID(data.project_id) if data.project_id else None,
    )
    db.add(report)
    await db.flush()
    report_id = str(report.id)
    await db.commit()

    background_tasks.add_task(_run_report, report_id, domain, data.niche)
    return report


@router.get("/", response_model=list[ReportOut])
async def list_reports(
    page: int = 1,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    result = await db.scalars(
        select(Report)
        .where(Report.user_id == user.id)
        .order_by(desc(Report.created_at))
        .offset(offset)
        .limit(limit)
    )
    return result.all()


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check cache
    cached = await cache_get(f"report:{report_id}")
    if cached:
        return cached

    report = await db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if str(report.user_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    if report.status == ReportStatus.DONE:
        await cache_set(f"report:{report_id}", report.__dict__, ttl=3600)

    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if str(report.user_id) != str(user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    await db.delete(report)
