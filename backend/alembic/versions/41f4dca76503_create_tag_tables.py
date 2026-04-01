"""create_tag_tables

Revision ID: 41f4dca76503
Revises: scan_ad_owner_not_null
Create Date: 2026-03-31 13:45:52.506315
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '41f4dca76503'
down_revision: Union[str, None] = 'scan_ad_owner_not_null'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=False),
        sa.Column('scope', sa.String(length=10), nullable=False),
        sa.Column('audit_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("scope IN ('global', 'audit')", name='ck_tag_scope'),
        sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'scope', 'audit_id', name='uq_tag_name_scope_audit'),
    )
    with op.batch_alter_table('tags', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tags_audit_id'), ['audit_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_tags_created_by'), ['created_by'], unique=False)
        batch_op.create_index(
            'uix_global_tag_name', ['name'], unique=True,
            sqlite_where=sa.text("scope = 'global' AND audit_id IS NULL"),
            postgresql_where=sa.text("scope = 'global' AND audit_id IS NULL"),
        )

    op.create_table(
        'tag_associations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('taggable_type', sa.String(length=50), nullable=False),
        sa.Column('taggable_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tag_id', 'taggable_type', 'taggable_id', name='uq_tag_assoc'),
    )
    with op.batch_alter_table('tag_associations', schema=None) as batch_op:
        batch_op.create_index('ix_tag_assoc_entity', ['taggable_type', 'taggable_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_tag_associations_tag_id'), ['tag_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('tag_associations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tag_associations_tag_id'))
        batch_op.drop_index('ix_tag_assoc_entity')
    op.drop_table('tag_associations')

    with op.batch_alter_table('tags', schema=None) as batch_op:
        batch_op.drop_index(
            'uix_global_tag_name',
            sqlite_where=sa.text("scope = 'global' AND audit_id IS NULL"),
            postgresql_where=sa.text("scope = 'global' AND audit_id IS NULL"),
        )
        batch_op.drop_index(batch_op.f('ix_tags_created_by'))
        batch_op.drop_index(batch_op.f('ix_tags_audit_id'))
    op.drop_table('tags')
