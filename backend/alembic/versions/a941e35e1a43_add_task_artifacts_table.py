"""add_task_artifacts_table

Revision ID: a941e35e1a43
Revises: b8e4c3d91f02
Create Date: 2026-03-28 18:57:48.557007
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a941e35e1a43'
down_revision: Union[str, None] = 'b8e4c3d91f02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('task_artifacts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agent_task_id', sa.Integer(), nullable=False),
        sa.Column('file_uuid', sa.String(length=36), nullable=False),
        sa.Column('original_filename', sa.String(length=500), nullable=False),
        sa.Column('stored_filename', sa.String(length=500), nullable=False),
        sa.Column('mime_type', sa.String(length=200), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('encrypted_dek', sa.LargeBinary(), nullable=True),
        sa.Column('dek_nonce', sa.LargeBinary(), nullable=True),
        sa.Column('kek_version', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_task_id'], ['agent_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_uuid')
    )
    with op.batch_alter_table('task_artifacts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_task_artifacts_agent_task_id'), ['agent_task_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('task_artifacts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_task_artifacts_agent_task_id'))
    op.drop_table('task_artifacts')
