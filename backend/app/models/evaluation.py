import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, Float, DateTime, Date, Text, ForeignKey, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class EvaluationStatus(str, PyEnum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Status tracking
    status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus, values_callable=lambda x: [e.value for e in x]),
        default=EvaluationStatus.PENDING, nullable=False
    )
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # S3 keys
    audio_s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    transcript_s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    report_s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Audio stats
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    student_speaking_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Metadata
    student_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evaluator_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evaluation_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Results
    cefr_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sub_level_rule: Mapped[str | None] = mapped_column(String(5), nullable=True)
    communicative_profile_fr: Mapped[str | None] = mapped_column(String(255), nullable=True)
    communicative_profile_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    global_comment_fr: Mapped[str | None] = mapped_column(Text, nullable=True)
    global_comment_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="evaluations")
