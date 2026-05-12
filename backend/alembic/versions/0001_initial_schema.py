"""Initial migration - create all tables

Revision ID: 0001
Revises: 
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # accounts
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "type",
            sa.Enum("checking", "savings", "cash", name="account_type_enum"),
            nullable=False,
        ),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column("initial_balance", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # credit_cards
    op.create_table(
        "credit_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("closing_day", sa.Integer, nullable=False),
        sa.Column("due_day", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column("credit_limit", sa.Numeric(15, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # transactions
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "type",
            sa.Enum("income", "expense", name="transaction_type_enum"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("is_recurring", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("recurrence_rule", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # credit_card_purchases
    op.create_table(
        "credit_card_purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("credit_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("installments", sa.Integer, nullable=False, server_default="1"),
        sa.Column("installment_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("purchase_date", sa.Date, nullable=False),
        sa.Column("first_installment_date", sa.Date, nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # installments
    op.create_table(
        "installments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("credit_card_purchases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("installment_number", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("is_paid", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Indexes
    op.create_index("ix_transactions_date", "transactions", ["date"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_installments_due_date", "installments", ["due_date"])
    op.create_index("ix_installments_purchase_id", "installments", ["purchase_id"])
    op.create_index("ix_purchases_credit_card_id", "credit_card_purchases", ["credit_card_id"])


def downgrade() -> None:
    op.drop_table("installments")
    op.drop_table("credit_card_purchases")
    op.drop_table("transactions")
    op.drop_table("credit_cards")
    op.drop_table("accounts")
    op.execute("DROP TYPE IF EXISTS account_type_enum")
    op.execute("DROP TYPE IF EXISTS transaction_type_enum")
