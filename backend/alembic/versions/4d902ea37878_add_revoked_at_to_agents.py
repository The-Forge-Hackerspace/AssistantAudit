"""add_revoked_at_to_agents

Revision ID: 4d902ea37878
Revises: 545ae2396390
Create Date: 2026-03-27 07:51:02.079264
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '4d902ea37878'
down_revision: Union[str, None] = '545ae2396390'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.drop_column('revoked_at')
