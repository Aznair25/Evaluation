"""Remove log_s3_key from evaluations

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("evaluations", "log_s3_key")


def downgrade() -> None:
    op.add_column(
        "evaluations",
        sa.Column("log_s3_key", sa.String(512), nullable=True),
    )
