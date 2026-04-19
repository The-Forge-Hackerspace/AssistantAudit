"""pipeline_uses_agent_nmap

Remplace la référence scan_id (ScanReseau local) par agent_id + scan_task_uuid
sur collect_pipelines pour que le scan Nmap soit délégué à un agent.

Revision ID: 8cd801626d19
Revises: 5fe6333fd834
Create Date: 2026-04-17 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '8cd801626d19'
down_revision: Union[str, None] = '5fe6333fd834'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('collect_pipelines', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_collect_pipelines_scan_id'))
        batch_op.drop_column('scan_id')
        batch_op.add_column(sa.Column('agent_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('scan_task_uuid', sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f('ix_collect_pipelines_agent_id'), ['agent_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_collect_pipelines_scan_task_uuid'), ['scan_task_uuid'], unique=False)
        batch_op.create_foreign_key(
            'fk_collect_pipelines_agent_id_agents',
            'agents',
            ['agent_id'],
            ['id'],
        )
        batch_op.create_foreign_key(
            'fk_collect_pipelines_scan_task_uuid_agent_tasks',
            'agent_tasks',
            ['scan_task_uuid'],
            ['task_uuid'],
        )


def downgrade() -> None:
    with op.batch_alter_table('collect_pipelines', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_collect_pipelines_scan_task_uuid'))
        batch_op.drop_index(batch_op.f('ix_collect_pipelines_agent_id'))
        batch_op.drop_column('scan_task_uuid')
        batch_op.drop_column('agent_id')
        batch_op.add_column(sa.Column('scan_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_collect_pipelines_scan_id_scans_reseau',
            'scans_reseau',
            ['scan_id'],
            ['id'],
        )
        batch_op.create_index(batch_op.f('ix_collect_pipelines_scan_id'), ['scan_id'], unique=False)
