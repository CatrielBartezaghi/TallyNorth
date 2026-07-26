"""Add ChatGPT integration tokens and action idempotency records.

Revision ID: 202607260001
Revises: 202605120000
Create Date: 2026-07-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202607260001"
down_revision = "202605120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=20), nullable=False),
        sa.Column("scopes", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_integration_tokens_token_hash",
        "integration_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_integration_tokens_user_id",
        "integration_tokens",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "gpt_action_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "integration_token_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["integration_token_id"],
            ["integration_tokens.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "operation",
            "idempotency_key",
            name="uq_gpt_action_request_user_operation_key",
        ),
    )
    op.create_index(
        "ix_gpt_action_requests_user_id",
        "gpt_action_requests",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gpt_action_requests_user_id",
        table_name="gpt_action_requests",
    )
    op.drop_table("gpt_action_requests")
    op.drop_index(
        "ix_integration_tokens_user_id",
        table_name="integration_tokens",
    )
    op.drop_index(
        "ix_integration_tokens_token_hash",
        table_name="integration_tokens",
    )
    op.drop_table("integration_tokens")
