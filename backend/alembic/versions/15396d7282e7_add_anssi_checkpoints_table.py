"""add_anssi_checkpoints_table

Revision ID: 15396d7282e7
Revises: 553fec46eb0a
Create Date: 2026-03-26 21:22:42.484298
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision: str = '15396d7282e7'
down_revision: Union[str, None] = '553fec46eb0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('anssi_checkpoints',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('vuln_id', sa.String(length=100), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('title_fr', sa.String(length=500), nullable=False),
    sa.Column('title_en', sa.String(length=500), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('recommendation', sa.Text(), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=False),
    sa.Column('required_attributes', sqlite.JSON(), nullable=False),
    sa.Column('target_object_types', sqlite.JSON(), nullable=False),
    sa.Column('auto_checkable', sa.Boolean(), nullable=False),
    sa.Column('severity_score', sa.Integer(), nullable=False),
    sa.Column('reference_url', sa.String(length=500), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('anssi_checkpoints', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_anssi_checkpoints_level'), ['level'], unique=False)
        batch_op.create_index(batch_op.f('ix_anssi_checkpoints_vuln_id'), ['vuln_id'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('anssi_checkpoints', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_anssi_checkpoints_vuln_id'))
        batch_op.drop_index(batch_op.f('ix_anssi_checkpoints_level'))

    op.drop_table('anssi_checkpoints')
