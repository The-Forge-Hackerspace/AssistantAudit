"""merge_heads

Revision ID: merge_heads_001
Revises: a941e35e1a43, c3f7a1b92d04
Create Date: 2026-03-29 16:13:58.130938
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'merge_heads_001'
down_revision: Union[str, None] = ('a941e35e1a43', 'c3f7a1b92d04')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
