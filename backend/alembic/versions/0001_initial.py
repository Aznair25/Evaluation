"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("google_id", sa.String(128), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("picture_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_google_id", "users", ["google_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Enum("pending", "transcribing", "analyzing", "generating_report", "completed", "failed", name="evaluationstatus"), nullable=False, server_default="pending"),
        sa.Column("progress_percentage", sa.Integer, default=0),
        sa.Column("current_step", sa.String(255), nullable=True),
        sa.Column("audio_s3_key", sa.String(512), nullable=True),
        sa.Column("transcript_s3_key", sa.String(512), nullable=True),
        sa.Column("report_s3_key", sa.String(512), nullable=True),
        sa.Column("audio_duration_seconds", sa.Float, nullable=True),
        sa.Column("student_speaking_duration_seconds", sa.Float, nullable=True),
        sa.Column("student_name", sa.String(255), nullable=True),
        sa.Column("evaluator_name", sa.String(255), nullable=True),
        sa.Column("institution", sa.String(255), nullable=True),
        sa.Column("evaluation_date", sa.Date, nullable=True),
        sa.Column("cefr_level", sa.String(10), nullable=True),
        sa.Column("sub_level_rule", sa.String(5), nullable=True),
        sa.Column("communicative_profile_fr", sa.String(255), nullable=True),
        sa.Column("communicative_profile_en", sa.String(255), nullable=True),
        sa.Column("global_comment_fr", sa.Text, nullable=True),
        sa.Column("global_comment_en", sa.Text, nullable=True),
        sa.Column("criteria_results", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_evaluations_user_id", "evaluations", ["user_id"])


def downgrade() -> None:
    op.drop_table("evaluations")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS evaluationstatus")
