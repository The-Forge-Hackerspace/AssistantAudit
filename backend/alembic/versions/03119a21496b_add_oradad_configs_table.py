"""add_oradad_configs_table

Revision ID: 03119a21496b
Revises: 4d902ea37878
Create Date: 2026-03-27 11:41:22.300309
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '03119a21496b'
down_revision: Union[str, None] = '4d902ea37878'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'oradad_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('auto_get_domain', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('auto_get_trusts', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('level', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('confidential', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('process_sysvol', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('sysvol_filter', sa.Text(), nullable=True),
        sa.Column('output_files', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('output_mla', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('sleep_time', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('explicit_domains', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('oradad_configs', schema=None) as batch_op:
        batch_op.create_index('ix_oradad_configs_owner_id', ['owner_id'])


def downgrade() -> None:
    with op.batch_alter_table('oradad_configs', schema=None) as batch_op:
        batch_op.drop_index('ix_oradad_configs_owner_id')
    op.drop_table('oradad_configs')
