"""create_report_tables

Revision ID: a11a330219bb
Revises: 43d973779ca0
Create Date: 2026-03-31 17:55:53.742803
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a11a330219bb'
down_revision: Union[str, None] = '43d973779ca0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('audit_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('template_name', sa.String(length=100), nullable=False),
        sa.Column('consultant_logo_path', sa.String(length=500), nullable=True),
        sa.Column('client_logo_path', sa.String(length=500), nullable=True),
        sa.Column('consultant_name', sa.String(length=200), nullable=True),
        sa.Column('consultant_contact', sa.Text(), nullable=True),
        sa.Column('pdf_path', sa.String(length=500), nullable=True),
        sa.Column('docx_path', sa.String(length=500), nullable=True),
        sa.Column('generated_by', sa.Integer(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'generating', 'ready', 'error')", name='ck_report_status'),
        sa.CheckConstraint("template_name IN ('complete', 'light', 'compliance')", name='ck_report_template'),
        sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_reports', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_reports_audit_id'), ['audit_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_reports_generated_by'), ['generated_by'], unique=False)

    op.create_table(
        'report_sections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('section_key', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('included', sa.Boolean(), nullable=False),
        sa.Column('custom_content', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['report_id'], ['audit_reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_id', 'section_key', name='uq_report_section_key'),
    )
    with op.batch_alter_table('report_sections', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_report_sections_report_id'), ['report_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('report_sections', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_report_sections_report_id'))
    op.drop_table('report_sections')

    with op.batch_alter_table('audit_reports', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_reports_generated_by'))
        batch_op.drop_index(batch_op.f('ix_audit_reports_audit_id'))
    op.drop_table('audit_reports')
