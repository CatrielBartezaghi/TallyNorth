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


LEGACY_COLUMNS = (
    "parent_id",
    "end_date",
    "recurrence_rule",
    "is_recurring",
)


def upgrade() -> None:
    """Destructively remove the retired transaction recurrence model.

    Production may already have some or all legacy columns removed. Keep this
    migration idempotent so a partially-cleaned database can still advance to
    the canonical RecurringEntry-only schema.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("transactions")}

    # Delete legacy templates/generated children only when the columns needed
    # to identify them still exist. Data loss here is intentional: the old
    # transaction-based recurrence model has been retired.
    legacy_predicates: list[str] = []
    if "is_recurring" in columns:
        legacy_predicates.append("is_recurring IS TRUE")
    if "parent_id" in columns:
        legacy_predicates.append("parent_id IS NOT NULL")

    if legacy_predicates:
        op.execute(
            sa.text(
                "DELETE FROM transactions WHERE " + " OR ".join(legacy_predicates)
            )
        )

    if "parent_id" in columns:
        foreign_keys = {
            foreign_key.get("name")
            for foreign_key in inspector.get_foreign_keys("transactions")
        }
        if "transactions_parent_id_fkey" in foreign_keys:
            op.drop_constraint(
                "transactions_parent_id_fkey",
                "transactions",
                type_="foreignkey",
            )

    for column_name in LEGACY_COLUMNS:
        if column_name in columns:
            op.drop_column("transactions", column_name)


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
