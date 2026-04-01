"""add_audit_intervention_fields

Revision ID: fee3cc8b8c35
Revises: a11a330219bb
Create Date: 2026-03-31 18:53:27.932258
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision: str = 'fee3cc8b8c35'
down_revision: Union[str, None] = 'a11a330219bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('audits', schema=None) as batch_op:
        batch_op.add_column(sa.Column('date_fin', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('client_contact_name', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('client_contact_title', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('client_contact_email', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('client_contact_phone', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('access_level', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('access_missing_details', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('intervention_window', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('intervention_constraints', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('scope_covered', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('scope_excluded', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('audit_type', sa.String(length=30), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('audits', schema=None) as batch_op:
        batch_op.drop_column('audit_type')
        batch_op.drop_column('scope_excluded')
        batch_op.drop_column('scope_covered')
        batch_op.drop_column('intervention_constraints')
        batch_op.drop_column('intervention_window')
        batch_op.drop_column('access_missing_details')
        batch_op.drop_column('access_level')
        batch_op.drop_column('client_contact_phone')
        batch_op.drop_column('client_contact_email')
        batch_op.drop_column('client_contact_title')
        batch_op.drop_column('client_contact_name')
        batch_op.drop_column('date_fin')
