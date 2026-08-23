"""Add recurring occurrence settlement tracking.

Revision ID: 20260823occurrences
Revises: 20260818droplegacy
Create Date: 2026-08-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260823occurrences"
down_revision: Union[str, None] = "20260818droplegacy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


settlement_mode_enum = postgresql.ENUM(
    "automatic",
    "manual",
    name="recurring_settlement_mode_enum",
    create_type=False,
)
occurrence_status_enum = postgresql.ENUM(
    "pending",
    "settled",
    "skipped",
    name="recurring_occurrence_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    settlement_mode_enum.create(bind, checkfirst=True)
    occurrence_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "recurring_entries",
        sa.Column(
            "settlement_mode",
            settlement_mode_enum,
            nullable=False,
            server_default="automatic",
        ),
    )

    op.create_table(
        "recurring_occurrences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("recurring_entry_id", sa.UUID(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("status", occurrence_status_enum, nullable=False, server_default="pending"),
        sa.Column("transaction_id", sa.UUID(), nullable=True),
        sa.Column("purchase_id", sa.UUID(), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["recurring_entry_id"],
            ["recurring_entries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["credit_card_purchases.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recurring_entry_id",
            "scheduled_date",
            name="uq_recurring_occurrence_entry_date",
        ),
    )
    op.create_index(
        "ix_recurring_occurrences_user_status_date",
        "recurring_occurrences",
        ["user_id", "status", "scheduled_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recurring_occurrences_user_status_date",
        table_name="recurring_occurrences",
    )
    op.drop_table("recurring_occurrences")
    op.drop_column("recurring_entries", "settlement_mode")

    bind = op.get_bind()
    occurrence_status_enum.drop(bind, checkfirst=True)
    settlement_mode_enum.drop(bind, checkfirst=True)
