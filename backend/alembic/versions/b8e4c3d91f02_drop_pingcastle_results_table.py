"""drop pingcastle_results table

Revision ID: b8e4c3d91f02
Revises: a7f3b2c41d58
Create Date: 2026-03-28 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b8e4c3d91f02'
down_revision: Union[str, None] = 'a7f3b2c41d58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('pingcastle_results')


def downgrade() -> None:
    op.create_table(
        'pingcastle_results',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('equipement_id', sa.Integer(), sa.ForeignKey('equipements.id'), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='running'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('target_host', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('global_score', sa.Integer(), nullable=True),
        sa.Column('stale_objects_score', sa.Integer(), nullable=True),
        sa.Column('privileged_accounts_score', sa.Integer(), nullable=True),
        sa.Column('trust_score', sa.Integer(), nullable=True),
        sa.Column('anomaly_score', sa.Integer(), nullable=True),
        sa.Column('maturity_level', sa.Integer(), nullable=True),
        sa.Column('risk_rules', sa.JSON(), nullable=True),
        sa.Column('domain_info', sa.JSON(), nullable=True),
        sa.Column('raw_report', sa.JSON(), nullable=True),
        sa.Column('findings', sa.JSON(), nullable=True),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('report_html_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
    )
    op.create_index('ix_pingcastle_results_equipement_id', 'pingcastle_results', ['equipement_id'])
