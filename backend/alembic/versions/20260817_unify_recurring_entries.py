"""Unify recurring entries across accounts and credit cards.

Revision ID: 20260817recurring
Revises: 959b4e9245a7
Create Date: 2026-08-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260817recurring"
down_revision: Union[str, None] = "959b4e9245a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    recurring_type = sa.Enum("income", "expense", name="recurring_entry_type_enum")
    recurring_frequency = sa.Enum("weekly", "monthly", "yearly", name="recurring_frequency_enum")
    recurring_destination = sa.Enum("account", "credit_card", name="recurring_destination_type_enum")

    recurring_type.create(op.get_bind(), checkfirst=True)
    recurring_frequency.create(op.get_bind(), checkfirst=True)
    recurring_destination.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "recurring_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("type", recurring_type, nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("frequency", recurring_frequency, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("destination_type", recurring_destination, nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("credit_card_id", sa.UUID(), nullable=True),
        sa.Column("last_generated_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(destination_type = 'account' AND account_id IS NOT NULL AND credit_card_id IS NULL) "
            "OR (destination_type = 'credit_card' AND credit_card_id IS NOT NULL AND account_id IS NULL)",
            name="ck_recurring_entry_exactly_one_destination",
        ),
        sa.CheckConstraint(
            "type = 'expense' OR destination_type = 'account'",
            name="ck_recurring_entry_income_requires_account",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["credit_card_id"], ["credit_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("transactions", sa.Column("recurring_entry_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_transactions_recurring_entry_id",
        "transactions",
        "recurring_entries",
        ["recurring_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_transaction_recurring_occurrence",
        "transactions",
        ["recurring_entry_id", "date"],
    )

    op.add_column("credit_card_purchases", sa.Column("recurring_entry_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_credit_card_purchases_recurring_entry_id",
        "credit_card_purchases",
        "recurring_entries",
        ["recurring_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_card_purchase_recurring_occurrence",
        "credit_card_purchases",
        ["recurring_entry_id", "purchase_date"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_card_purchase_recurring_occurrence", "credit_card_purchases", type_="unique")
    op.drop_constraint("fk_credit_card_purchases_recurring_entry_id", "credit_card_purchases", type_="foreignkey")
    op.drop_column("credit_card_purchases", "recurring_entry_id")

    op.drop_constraint("uq_transaction_recurring_occurrence", "transactions", type_="unique")
    op.drop_constraint("fk_transactions_recurring_entry_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "recurring_entry_id")

    op.drop_table("recurring_entries")
    sa.Enum(name="recurring_destination_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="recurring_frequency_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="recurring_entry_type_enum").drop(op.get_bind(), checkfirst=True)
