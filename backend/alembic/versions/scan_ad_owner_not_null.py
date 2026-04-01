"""owner_id NOT NULL sur scans_reseau et ad_audit_results

Revision ID: scan_ad_owner_not_null
Revises: add_entreprise_owner_id
Create Date: 2026-03-30

Rend owner_id NOT NULL sur scans_reseau et ad_audit_results.
Les NULL résiduels sont assignés au premier admin (ou supprimés s'il n'y a pas d'admin).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


revision: str = 'scan_ad_owner_not_null'
down_revision: Union[str, None] = 'add_entreprise_owner_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    admin = conn.execute(text("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1")).first()

    if admin:
        admin_id = admin[0]
        conn.execute(text(f"UPDATE scans_reseau SET owner_id = {admin_id} WHERE owner_id IS NULL"))
        conn.execute(text(f"UPDATE ad_audit_results SET owner_id = {admin_id} WHERE owner_id IS NULL"))
    else:
        conn.execute(text("DELETE FROM scans_reseau WHERE owner_id IS NULL"))
        conn.execute(text("DELETE FROM ad_audit_results WHERE owner_id IS NULL"))

    with op.batch_alter_table("scans_reseau") as batch_op:
        batch_op.alter_column(
            "owner_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    with op.batch_alter_table("ad_audit_results") as batch_op:
        batch_op.alter_column(
            "owner_id",
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("ad_audit_results") as batch_op:
        batch_op.alter_column(
            "owner_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

    with op.batch_alter_table("scans_reseau") as batch_op:
        batch_op.alter_column(
            "owner_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
