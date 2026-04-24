import uuid
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.database import Base, get_db
from app.auth.dependencies import get_current_user, require_verified
from app.auth.models import User


# ── Model ─────────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    niche: Mapped[str | None] = mapped_column(String(255), nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="projects", lazy="selectin")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="project", lazy="selectin")  # noqa: F821


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    domain: str | None = None
    niche: str | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    domain: str | None
    niche: str | None
    report_count: int
    created_at: str

    class Config:
        from_attributes = True


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    project = Project(owner_id=user.id, **data.model_dump())
    db.add(project)
    await db.flush()
    return {**project.__dict__, "report_count": 0}


@router.get("/", response_model=list[ProjectOut])
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.scalars(
        select(Project).where(Project.owner_id == user.id).order_by(desc(Project.created_at))
    )
    projects = result.all()
    return [
        {**p.__dict__, "report_count": len(p.reports)} for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if str(project.owner_id) != str(user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    return {**project.__dict__, "report_count": len(project.reports)}


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    data: ProjectCreate,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or str(project.owner_id) != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    return {**project.__dict__, "report_count": len(project.reports)}


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or str(project.owner_id) != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    await db.delete(project)
