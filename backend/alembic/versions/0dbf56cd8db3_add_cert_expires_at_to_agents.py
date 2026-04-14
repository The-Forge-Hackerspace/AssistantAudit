"""add_cert_expires_at_to_agents

Revision ID: 0dbf56cd8db3
Revises: 3a7f2c8d1e90
Create Date: 2026-04-03 16:19:23.273842
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# Variables requises par le runner Alembic (lecture introspective via execfile),
# expose-les explicitement pour eviter les avertissements 'unused global'.
__all__ = ("revision", "down_revision", "branch_labels", "depends_on", "upgrade", "downgrade")

revision: str = '0dbf56cd8db3'
down_revision: Union[str, None] = '3a7f2c8d1e90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cert_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.drop_column('cert_expires_at')
