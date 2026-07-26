"""Store cached results for expanded GPT Actions.

Revision ID: 202607260002
Revises: 202607260001
Create Date: 2026-07-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202607260002"
down_revision = "202607260001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gpt_action_requests",
        sa.Column("response_payload", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gpt_action_requests", "response_payload")
