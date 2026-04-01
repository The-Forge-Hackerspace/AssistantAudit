"""add owner_id to entreprises

Revision ID: add_entreprise_owner_id
Revises: backfill_owner_id
Create Date: 2026-03-30

Adds owner_id FK to entreprises table with 3-step migration:
1. Add nullable column
2. Backfill from first linked audit, fallback to first admin
3. Make NOT NULL
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'add_entreprise_owner_id'
down_revision: Union[str, None] = 'backfill_owner_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add nullable column
    with op.batch_alter_table("entreprises") as batch_op:
        batch_op.add_column(
            sa.Column("owner_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index("ix_entreprises_owner_id", ["owner_id"])

    # Step 2: Backfill from first linked audit's owner_id
    op.execute(
        "UPDATE entreprises SET owner_id = ("
        "  SELECT audits.owner_id FROM audits"
        "  WHERE audits.entreprise_id = entreprises.id"
        "  ORDER BY audits.id LIMIT 1"
        ") WHERE owner_id IS NULL"
    )

    # Step 2b: Fallback — entreprises without any audit get first admin
    op.execute(
        "UPDATE entreprises SET owner_id = ("
        "  SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"
        ") WHERE owner_id IS NULL"
    )

    # Step 2c: Ultimate fallback — first user if no admin exists
    op.execute(
        "UPDATE entreprises SET owner_id = ("
        "  SELECT id FROM users ORDER BY id LIMIT 1"
        ") WHERE owner_id IS NULL"
    )

    # Step 3: Make NOT NULL and add FK
    with op.batch_alter_table("entreprises") as batch_op:
        batch_op.alter_column("owner_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_entreprises_owner_id", "users", ["owner_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("entreprises") as batch_op:
        batch_op.drop_constraint("fk_entreprises_owner_id", type_="foreignkey")
        batch_op.drop_index("ix_entreprises_owner_id")
        batch_op.drop_column("owner_id")
