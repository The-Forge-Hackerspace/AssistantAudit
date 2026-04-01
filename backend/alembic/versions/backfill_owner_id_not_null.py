"""backfill owner_id and make NOT NULL on audits

Revision ID: backfill_owner_id
Revises: merge_heads_001
Create Date: 2026-03-29

Backfills NULL owner_id values with the first admin user ID, then makes
audits.owner_id NOT NULL. scans_reseau and ad_audit_results are backfilled
but remain nullable.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'backfill_owner_id'
down_revision: Union[str, None] = 'merge_heads_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill audits.owner_id with first admin user
    op.execute(
        "UPDATE audits SET owner_id = ("
        "SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"
        ") WHERE owner_id IS NULL"
    )
    # Make audits.owner_id NOT NULL
    with op.batch_alter_table("audits") as batch_op:
        batch_op.alter_column(
            "owner_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    # Backfill scans_reseau.owner_id (keep nullable)
    op.execute(
        "UPDATE scans_reseau SET owner_id = ("
        "SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"
        ") WHERE owner_id IS NULL"
    )

    # Backfill ad_audit_results.owner_id (keep nullable)
    op.execute(
        "UPDATE ad_audit_results SET owner_id = ("
        "SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"
        ") WHERE owner_id IS NULL"
    )


def downgrade() -> None:
    # Revert audits.owner_id to nullable
    with op.batch_alter_table("audits") as batch_op:
        batch_op.alter_column(
            "owner_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
