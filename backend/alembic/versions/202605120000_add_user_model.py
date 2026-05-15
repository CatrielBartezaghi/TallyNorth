"""Add user model and user_id to all tables

Revision ID: 202605120000
Revises: 16a2a7915204
Create Date: 2026-05-12 20:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
import datetime

# revision identifiers, used by Alembic.
revision: str = '202605120000'
down_revision: Union[str, None] = '16a2a7915204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create users table
    users_table = op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Insert a default user so we can assign existing data to it
    # We use a dummy hash since it's just for existing local data
    default_user_id = str(uuid.uuid4())
    op.execute(
        f"INSERT INTO users (id, email, hashed_password) VALUES "
        f"('{default_user_id}', 'default_migration_user@example.com', 'dummyhash')"
    )

    # 3. Add user_id to other tables
    tables = [
        'accounts', 'budgets', 'categories', 'credit_cards', 
        'installments', 'investments', 'credit_card_purchases', 
        'saving_goals', 'transactions'
    ]
    
    for table in tables:
        # Add column as nullable first
        op.add_column(table, sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
        
        # Populate with default user
        op.execute(f"UPDATE {table} SET user_id = '{default_user_id}' WHERE user_id IS NULL")
        
        # Alter to not nullable
        op.alter_column(table, 'user_id', existing_type=postgresql.UUID(as_uuid=True), nullable=False)
        
        # Add foreign key
        op.create_foreign_key(f"fk_{table}_user_id", table, 'users', ['user_id'], ['id'])

def downgrade() -> None:
    tables = [
        'accounts', 'budgets', 'categories', 'credit_cards', 
        'installments', 'investments', 'credit_card_purchases', 
        'saving_goals', 'transactions'
    ]
    
    for table in tables:
        op.drop_constraint(f"fk_{table}_user_id", table, type_='foreignkey')
        op.drop_column(table, 'user_id')
        
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
