"""add_control_effort_days

Revision ID: e9fac305c5bf
Revises: 9a4e7cd1a2f3
Create Date: 2026-04-27 11:39:29.640433
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e9fac305c5bf'
down_revision: Union[str, None] = '9a4e7cd1a2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "controls",
        sa.Column("effort_days", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("controls", "effort_days")
