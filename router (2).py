from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.auth.dependencies import require_admin
from app.auth.models import User, UserRole
from app.reports.models import Report, ReportStatus
from app.subscriptions.models import Subscription, PlanName

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
async def get_stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    total_users = await db.scalar(select(func.count(User.id)))
    new_users = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
    )
    total_reports = await db.scalar(select(func.count(Report.id)))
    reports_this_month = await db.scalar(
        select(func.count(Report.id)).where(Report.created_at >= thirty_days_ago)
    )

    # Plan distribution
    plan_counts = {}
    for plan in PlanName:
        count = await db.scalar(
            select(func.count(Subscription.id)).where(Subscription.plan == plan)
        )
        plan_counts[plan] = count or 0

    # Free users (no subscription)
    paying = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.plan != PlanName.FREE, Subscription.is_active == True
        )
    )

    return {
        "users": {
            "total": total_users,
            "new_30d": new_users,
            "paying": paying,
        },
        "reports": {
            "total": total_reports,
            "this_month": reports_this_month,
        },
        "plans": plan_counts,
        "mrr_estimate": (
            (plan_counts.get(PlanName.STARTER, 0) * 29) +
            (plan_counts.get(PlanName.PRO, 0) * 79) +
            (plan_counts.get(PlanName.AGENCY, 0) * 199)
        ),
    }


@router.get("/users")
async def list_users(
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(User).order_by(desc(User.created_at)).offset((page - 1) * limit).limit(limit)
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    users = await db.scalars(query)
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "plan": u.plan,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if str(user.id) == str(admin.id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate yourself")
    user.is_active = not user.is_active
    return {"is_active": user.is_active}


@router.patch("/users/{user_id}/role")
async def change_user_role(
    user_id: str,
    role: UserRole,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.role = role
    return {"role": user.role}


@router.get("/reports")
async def list_all_reports(
    page: int = 1,
    limit: int = 50,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.scalars(
        select(Report).order_by(desc(Report.created_at)).offset((page - 1) * limit).limit(limit)
    )
    return [
        {
            "id": str(r.id),
            "domain": r.domain,
            "status": r.status,
            "score_overall": r.score_overall,
            "user_email": r.user.email if r.user else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in result
    ]
