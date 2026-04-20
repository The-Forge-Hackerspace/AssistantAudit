"""collect_via_agent

Ajoute la colonne agent_task_id sur collect_results pour lier une collecte
SSH/WinRM a la tache agent qui l'execute (la collecte ne s'execute plus
cote serveur, mais est deleguee a un agent on-prem).

Revision ID: 9a4e7cd1a2f3
Revises: 8cd801626d19
Create Date: 2026-04-20 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '9a4e7cd1a2f3'
down_revision: Union[str, None] = '8cd801626d19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('collect_results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agent_task_id', sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_collect_results_agent_task_id'),
            ['agent_task_id'],
            unique=False,
        )
        batch_op.create_foreign_key(
            'fk_collect_results_agent_task_id_agent_tasks',
            'agent_tasks',
            ['agent_task_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('collect_results', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_collect_results_agent_task_id_agent_tasks',
            type_='foreignkey',
        )
        batch_op.drop_index(batch_op.f('ix_collect_results_agent_task_id'))
        batch_op.drop_column('agent_task_id')
