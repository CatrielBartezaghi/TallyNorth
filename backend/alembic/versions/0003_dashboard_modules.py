"""Add dashboard support modules

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-03
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    postgresql.ENUM("income", "expense", "both", name="category_type_enum").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("fixed_income", "fund", "stock", "crypto", "forex", "other", name="investment_type_enum").create(op.get_bind(), checkfirst=True)
    category_type = postgresql.ENUM("income", "expense", "both", name="category_type_enum", create_type=False)
    investment_type = postgresql.ENUM("fixed_income", "fund", "stock", "crypto", "forex", "other", name="investment_type_enum", create_type=False)

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("type", category_type, nullable=False, server_default="expense"),
        sa.Column("color", sa.String(20), nullable=False, server_default="#38bdf8"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)

    op.add_column("transactions", sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_transactions_category", "transactions", "categories", ["category_id"], ["id"], ondelete="SET NULL")
    op.add_column("credit_card_purchases", sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_purchases_category", "credit_card_purchases", "categories", ["category_id"], ["id"], ondelete="SET NULL")

    op.add_column("installments", sa.Column("paid_account_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("installments", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_installments_paid_account", "installments", "accounts", ["paid_account_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("currencies.id"), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_budgets_period_start", "budgets", ["period_start"])

    op.create_table(
        "saving_goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("currencies.id"), nullable=False),
        sa.Column("target_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("target_date", sa.Date, nullable=True),
        sa.Column("color", sa.String(20), nullable=False, server_default="#22c55e"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "investments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("type", investment_type, nullable=False, server_default="other"),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("currencies.id"), nullable=False),
        sa.Column("invested_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("current_value", sa.Numeric(15, 2), nullable=False),
        sa.Column("expected_return_rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "exchange_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("from_currency_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("currencies.id"), nullable=False),
        sa.Column("to_currency_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("currencies.id"), nullable=False),
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("from_currency_id", "to_currency_id", "date", name="uq_exchange_rate_pair_date"),
    )
    op.create_index("ix_exchange_rates_pair_date", "exchange_rates", ["from_currency_id", "to_currency_id", "date"])

    seed_categories()


def seed_categories() -> None:
    categories = sa.table(
        "categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("type", sa.String),
        sa.column("color", sa.String),
        sa.column("icon", sa.String),
    )
    op.bulk_insert(
        categories,
        [
            {"id": uuid.uuid4(), "name": "Sueldo", "type": "income", "color": "#22c55e", "icon": "briefcase"},
            {"id": uuid.uuid4(), "name": "Freelance", "type": "income", "color": "#14b8a6", "icon": "laptop"},
            {"id": uuid.uuid4(), "name": "Hogar", "type": "expense", "color": "#3b82f6", "icon": "home"},
            {"id": uuid.uuid4(), "name": "Comida", "type": "expense", "color": "#22c55e", "icon": "utensils"},
            {"id": uuid.uuid4(), "name": "Transporte", "type": "expense", "color": "#f59e0b", "icon": "car"},
            {"id": uuid.uuid4(), "name": "Salud", "type": "expense", "color": "#ec4899", "icon": "heart-pulse"},
            {"id": uuid.uuid4(), "name": "Ocio", "type": "expense", "color": "#8b5cf6", "icon": "gamepad-2"},
            {"id": uuid.uuid4(), "name": "Servicios", "type": "expense", "color": "#06b6d4", "icon": "receipt"},
            {"id": uuid.uuid4(), "name": "Educacion", "type": "expense", "color": "#f97316", "icon": "graduation-cap"},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_exchange_rates_pair_date", table_name="exchange_rates")
    op.drop_table("exchange_rates")
    op.drop_table("investments")
    op.drop_table("saving_goals")
    op.drop_index("ix_budgets_period_start", table_name="budgets")
    op.drop_table("budgets")
    op.drop_constraint("fk_installments_paid_account", "installments", type_="foreignkey")
    op.drop_column("installments", "paid_at")
    op.drop_column("installments", "paid_account_id")
    op.drop_constraint("fk_purchases_category", "credit_card_purchases", type_="foreignkey")
    op.drop_column("credit_card_purchases", "category_id")
    op.drop_constraint("fk_transactions_category", "transactions", type_="foreignkey")
    op.drop_column("transactions", "category_id")
    op.drop_index("ix_categories_name", table_name="categories")
    op.drop_table("categories")
    op.execute("DROP TYPE IF EXISTS investment_type_enum")
    op.execute("DROP TYPE IF EXISTS category_type_enum")
