import uuid
import enum
from sqlalchemy import String, Integer, Float, Text, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    niche: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ReportStatus] = mapped_column(SAEnum(ReportStatus), default=ReportStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scores
    score_overall: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_visibility: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_authority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_coverage: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Analysis data (stored as JSON)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    top_competitors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Export
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821
    project: Mapped["Project | None"] = relationship("Project", lazy="selectin")  # noqa: F821
