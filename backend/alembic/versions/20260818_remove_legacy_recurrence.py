"""Remove legacy transaction recurrence fields.

Revision ID: 20260818droplegacy
Revises: 20260817recurring
Create Date: 2026-08-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260818droplegacy"
down_revision: Union[str, None] = "20260817recurring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Legacy transaction templates and their generated children belong to the
    # retired recurrence model. RecurringEntry is the only recurrence source.
    op.execute(
        "DELETE FROM transactions WHERE is_recurring = TRUE OR parent_id IS NOT NULL"
    )
    op.drop_constraint(
        "transactions_parent_id_fkey",
        "transactions",
        type_="foreignkey",
    )
    op.drop_column("transactions", "parent_id")
    op.drop_column("transactions", "end_date")
    op.drop_column("transactions", "recurrence_rule")
    op.drop_column("transactions", "is_recurring")


def downgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "is_recurring",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "transactions",
        sa.Column("recurrence_rule", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("end_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("parent_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "transactions_parent_id_fkey",
        "transactions",
        "transactions",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
