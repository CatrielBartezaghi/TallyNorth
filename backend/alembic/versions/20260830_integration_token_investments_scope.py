"""Grant investments write scope to existing active integration tokens.

Revision ID: 20260830investmentscope
Revises: 20260829investmentledger
Create Date: 2026-08-30
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260830investmentscope"
down_revision: Union[str, None] = "20260829investmentledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tokens issued before the investment ledger rollout could not use the new
    # investment actions. Preserve the token secret and append the new scope.
    op.execute("""
        UPDATE integration_tokens
        SET scopes = trim(scopes || ' investments:write')
        WHERE revoked_at IS NULL
          AND (' ' || scopes || ' ') NOT LIKE '% investments:write %'
    """)


def downgrade() -> None:
    # Intentionally keep the permission on downgrade: we cannot distinguish
    # tokens that received it here from tokens explicitly granted by the user.
    pass
