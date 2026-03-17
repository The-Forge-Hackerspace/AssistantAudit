"""Add monkey365_scan_results table for Microsoft 365 audit tracking.

Stores Monkey365 scan results including config snapshots, findings count,
and timing metadata for Microsoft 365 / Azure AD audits.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_add_monkey365_scan_results"
down_revision: Union[str, None] = "006_add_vlan_definitions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "monkey365_scan_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entreprise_id", sa.Integer(), sa.ForeignKey("entreprises.id"), nullable=False, index=True),
        sa.Column("status", sa.Enum("running", "success", "failed", name="monkey365scanstatus"), nullable=False, server_default="running"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("scan_id", sa.String(100), nullable=False, unique=True),
        sa.Column("config_snapshot", sa.JSON(), nullable=True),
        sa.Column("output_path", sa.String(500), nullable=True),
        sa.Column("entreprise_slug", sa.String(200), nullable=True),
        sa.Column("findings_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("monkey365_scan_results")
