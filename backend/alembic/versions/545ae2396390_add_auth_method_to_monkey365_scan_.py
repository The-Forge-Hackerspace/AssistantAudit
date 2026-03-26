"""add_auth_method_to_monkey365_scan_results

Revision ID: 545ae2396390
Revises: 15396d7282e7
Create Date: 2026-03-26 23:04:51.230302
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '545ae2396390'
down_revision: Union[str, None] = '15396d7282e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('monkey365_scan_results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('auth_method', sa.String(length=50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('monkey365_scan_results', schema=None) as batch_op:
        batch_op.drop_column('auth_method')
