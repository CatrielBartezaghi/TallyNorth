"""Add investment ledger, valuations, and saving goal allocations.

Revision ID: 20260829investmentledger
Revises: 20260823occurrences
Create Date: 2026-08-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260829investmentledger"
down_revision: Union[str, None] = "20260823occurrences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


operation_type_values = ("opening", "buy", "sell", "dividend", "interest", "fee")


def upgrade() -> None:
    postgresql.ENUM(
        *operation_type_values,
        name="investment_operation_type_enum",
    ).create(op.get_bind(), checkfirst=True)
    operation_type_enum = postgresql.ENUM(
        *operation_type_values,
        name="investment_operation_type_enum",
        create_type=False,
    )

    op.add_column("investments", sa.Column("symbol", sa.String(32), nullable=True))
    op.add_column("investments", sa.Column("broker", sa.String(80), nullable=True))
    op.add_column("investments", sa.Column("quantity", sa.Numeric(24, 8), nullable=False, server_default="0"))
    op.add_column("investments", sa.Column("average_cost", sa.Numeric(18, 8), nullable=True))
    op.add_column("investments", sa.Column("realized_gain", sa.Numeric(15, 2), nullable=False, server_default="0"))
    op.add_column("investments", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_index("ix_investments_user_id", "investments", ["user_id"])

    op.create_table(
        "investment_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("investment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", operation_type_enum, nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("fee", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("amount > 0", name="ck_investment_operation_amount_positive"),
        sa.CheckConstraint("fee >= 0", name="ck_investment_operation_fee_nonnegative"),
        sa.CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_investment_operation_quantity_positive"),
    )
    op.create_index("ix_investment_operations_user_id", "investment_operations", ["user_id"])
    op.create_index("ix_investment_operations_investment_id", "investment_operations", ["investment_id"])
    op.create_index("ix_investment_operations_account_id", "investment_operations", ["account_id"])
    op.create_index("ix_investment_operations_date", "investment_operations", ["date"])

    op.create_table(
        "investment_valuations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("investment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", sa.Numeric(15, 2), nullable=False),
        sa.Column("valuation_date", sa.Date, nullable=False),
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("value >= 0", name="ck_investment_valuation_value_nonnegative"),
    )
    op.create_index("ix_investment_valuations_user_id", "investment_valuations", ["user_id"])
    op.create_index("ix_investment_valuations_investment_id", "investment_valuations", ["investment_id"])
    op.create_index("ix_investment_valuations_valuation_date", "investment_valuations", ["valuation_date"])

    op.create_table(
        "saving_goal_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("saving_goal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("saving_goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("investment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("allocation_percent", sa.Numeric(5, 2), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "(account_id IS NOT NULL AND investment_id IS NULL) OR "
            "(account_id IS NULL AND investment_id IS NOT NULL)",
            name="ck_saving_goal_allocation_one_source",
        ),
        sa.CheckConstraint(
            "allocation_percent > 0 AND allocation_percent <= 100",
            name="ck_saving_goal_allocation_percent",
        ),
    )
    op.create_index("ix_saving_goal_allocations_user_id", "saving_goal_allocations", ["user_id"])
    op.create_index("ix_saving_goal_allocations_saving_goal_id", "saving_goal_allocations", ["saving_goal_id"])

    # Preserve existing snapshots as an opening ledger entry plus an initial valuation.
    op.execute("""
        INSERT INTO investment_operations
            (id, user_id, investment_id, account_id, type, quantity, unit_price, amount, fee, date, notes, created_at)
        SELECT
            gen_random_uuid(), user_id, id, NULL, 'opening', NULL, NULL,
            invested_amount, 0, created_at::date, 'Migrated opening position', created_at
        FROM investments
        WHERE invested_amount > 0
    """)
    op.execute("""
        INSERT INTO investment_valuations
            (id, user_id, investment_id, value, valuation_date, source, notes, created_at)
        SELECT
            gen_random_uuid(), user_id, id, current_value, CURRENT_DATE,
            'migration', 'Migrated current valuation', now()
        FROM investments
    """)


def downgrade() -> None:
    op.drop_index("ix_saving_goal_allocations_saving_goal_id", table_name="saving_goal_allocations")
    op.drop_index("ix_saving_goal_allocations_user_id", table_name="saving_goal_allocations")
    op.drop_table("saving_goal_allocations")

    op.drop_index("ix_investment_valuations_valuation_date", table_name="investment_valuations")
    op.drop_index("ix_investment_valuations_investment_id", table_name="investment_valuations")
    op.drop_index("ix_investment_valuations_user_id", table_name="investment_valuations")
    op.drop_table("investment_valuations")

    op.drop_index("ix_investment_operations_date", table_name="investment_operations")
    op.drop_index("ix_investment_operations_account_id", table_name="investment_operations")
    op.drop_index("ix_investment_operations_investment_id", table_name="investment_operations")
    op.drop_index("ix_investment_operations_user_id", table_name="investment_operations")
    op.drop_table("investment_operations")

    op.drop_index("ix_investments_user_id", table_name="investments")
    op.drop_column("investments", "updated_at")
    op.drop_column("investments", "realized_gain")
    op.drop_column("investments", "average_cost")
    op.drop_column("investments", "quantity")
    op.drop_column("investments", "broker")
    op.drop_column("investments", "symbol")
    postgresql.ENUM(
        *operation_type_values,
        name="investment_operation_type_enum",
    ).drop(op.get_bind(), checkfirst=True)
