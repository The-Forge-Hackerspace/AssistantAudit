"""oradad_config_encrypted_domains

Change explicit_domains from JSON to Text (EncryptedText),
update auto_get_domain/trusts defaults to 0 (false).

Revision ID: a7f3b2c41d58
Revises: 03119a21496b
Create Date: 2026-03-27 12:10:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a7f3b2c41d58'
down_revision: Union[str, None] = '03119a21496b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite does not support ALTER COLUMN, so we use batch mode
    with op.batch_alter_table('oradad_configs', schema=None) as batch_op:
        # Change explicit_domains from JSON to Text (EncryptedText storage)
        batch_op.alter_column(
            'explicit_domains',
            type_=sa.Text(),
            existing_type=sa.JSON(),
            existing_nullable=True,
        )
        # Update defaults for auto_get_domain and auto_get_trusts
        batch_op.alter_column(
            'auto_get_domain',
            server_default='0',
            existing_type=sa.Boolean(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'auto_get_trusts',
            server_default='0',
            existing_type=sa.Boolean(),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('oradad_configs', schema=None) as batch_op:
        batch_op.alter_column(
            'explicit_domains',
            type_=sa.JSON(),
            existing_type=sa.Text(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'auto_get_domain',
            server_default='1',
            existing_type=sa.Boolean(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'auto_get_trusts',
            server_default='1',
            existing_type=sa.Boolean(),
            existing_nullable=False,
        )
