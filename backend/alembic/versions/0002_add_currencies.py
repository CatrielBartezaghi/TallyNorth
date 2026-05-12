"""Add currencies table and migrate currency FK on accounts and credit_cards

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-02
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Default currencies to seed
DEFAULT_CURRENCIES = [
    {"code": "ARS", "name": "Argentine Peso",   "symbol": "$",    "decimal_places": 2, "is_crypto": False},
    {"code": "USD", "name": "US Dollar",         "symbol": "U$D",  "decimal_places": 2, "is_crypto": False},
    {"code": "EUR", "name": "Euro",              "symbol": "€",    "decimal_places": 2, "is_crypto": False},
    {"code": "BRL", "name": "Brazilian Real",    "symbol": "R$",   "decimal_places": 2, "is_crypto": False},
    {"code": "BTC", "name": "Bitcoin",           "symbol": "₿",    "decimal_places": 8, "is_crypto": True},
    {"code": "ETH", "name": "Ethereum",          "symbol": "Ξ",    "decimal_places": 8, "is_crypto": True},
    {"code": "USDT","name": "Tether USD",        "symbol": "₮",    "decimal_places": 2, "is_crypto": True},
]


def upgrade() -> None:
    # 1. Create currencies table
    currencies_table = op.create_table(
        "currencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("decimal_places", sa.Integer, nullable=False, server_default="2"),
        sa.Column("is_crypto", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_currencies_code", "currencies", ["code"], unique=True)

    # 2. Seed default currencies and capture code→id mapping
    rows = [{"id": uuid.uuid4(), **c} for c in DEFAULT_CURRENCIES]
    op.bulk_insert(currencies_table, rows)

    code_to_id = {r["code"]: r["id"] for r in rows}
    ars_id = code_to_id["ARS"]  # fallback for any unknown code

    # 3. Add nullable currency_id to accounts
    op.add_column(
        "accounts",
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # 4. Populate from existing currency varchar
    conn = op.get_bind()
    for code, cid in code_to_id.items():
        conn.execute(
            sa.text("UPDATE accounts SET currency_id = :cid WHERE currency = :code"),
            {"cid": str(cid), "code": code},
        )
    # Fallback: any remaining rows get ARS
    conn.execute(
        sa.text("UPDATE accounts SET currency_id = :cid WHERE currency_id IS NULL"),
        {"cid": str(ars_id)},
    )
    # 5. Make NOT NULL and add FK
    op.alter_column("accounts", "currency_id", nullable=False)
    op.create_foreign_key("fk_accounts_currency", "accounts", "currencies", ["currency_id"], ["id"])
    # 6. Drop old column
    op.drop_column("accounts", "currency")

    # Repeat for credit_cards
    op.add_column(
        "credit_cards",
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    for code, cid in code_to_id.items():
        conn.execute(
            sa.text("UPDATE credit_cards SET currency_id = :cid WHERE currency = :code"),
            {"cid": str(cid), "code": code},
        )
    conn.execute(
        sa.text("UPDATE credit_cards SET currency_id = :cid WHERE currency_id IS NULL"),
        {"cid": str(ars_id)},
    )
    op.alter_column("credit_cards", "currency_id", nullable=False)
    op.create_foreign_key("fk_credit_cards_currency", "credit_cards", "currencies", ["currency_id"], ["id"])
    op.drop_column("credit_cards", "currency")


def downgrade() -> None:
    # Restore varchar columns
    op.add_column("accounts", sa.Column("currency", sa.String(3), nullable=True))
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE accounts SET currency = c.code FROM currencies c WHERE accounts.currency_id = c.id"
    ))
    op.alter_column("accounts", "currency", nullable=False)
    op.drop_constraint("fk_accounts_currency", "accounts", type_="foreignkey")
    op.drop_column("accounts", "currency_id")

    op.add_column("credit_cards", sa.Column("currency", sa.String(3), nullable=True))
    conn.execute(sa.text(
        "UPDATE credit_cards SET currency = c.code FROM currencies c WHERE credit_cards.currency_id = c.id"
    ))
    op.alter_column("credit_cards", "currency", nullable=False)
    op.drop_constraint("fk_credit_cards_currency", "credit_cards", type_="foreignkey")
    op.drop_column("credit_cards", "currency_id")

    op.drop_index("ix_currencies_code", table_name="currencies")
    op.drop_table("currencies")
