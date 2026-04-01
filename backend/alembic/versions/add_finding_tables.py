"""Ajout des tables finding et finding_status_history.

Revision ID: 3a7f2c8d1e90
Revises: fee3cc8b8c35
Create Date: 2026-04-01 12:25:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3a7f2c8d1e90"
down_revision = "fee3cc8b8c35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("control_result_id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "assigned", "in_progress", "remediated", "verified", "closed", name="findingstatus"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("remediation_note", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.String(200), nullable=True),
        sa.Column("duplicate_of_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["control_result_id"], ["control_results.id"]),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipements.id"]),
        sa.ForeignKeyConstraint(["duplicate_of_id"], ["findings.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index("ix_findings_control_result_id", "findings", ["control_result_id"])
    op.create_index("ix_findings_assessment_id", "findings", ["assessment_id"])
    op.create_index("ix_findings_equipment_id", "findings", ["equipment_id"])
    op.create_index("ix_findings_status", "findings", ["status"])

    op.create_table(
        "finding_status_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("finding_id", sa.Integer(), nullable=False),
        sa.Column(
            "old_status",
            sa.Enum("open", "assigned", "in_progress", "remediated", "verified", "closed", name="findingstatus"),
            nullable=False,
        ),
        sa.Column(
            "new_status",
            sa.Enum("open", "assigned", "in_progress", "remediated", "verified", "closed", name="findingstatus"),
            nullable=False,
        ),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"]),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
    )
    op.create_index("ix_finding_status_history_finding_id", "finding_status_history", ["finding_id"])


def downgrade() -> None:
    op.drop_table("finding_status_history")
    op.drop_table("findings")
