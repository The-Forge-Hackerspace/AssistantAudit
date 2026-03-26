"""create_agents_and_agent_tasks_tables

Revision ID: 6e27188411e6
Revises: 5f73dd19afec
Create Date: 2026-03-26 16:37:47.760547
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '6e27188411e6'
down_revision: Union[str, None] = '5f73dd19afec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Creer la table agents
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_uuid", sa.String(36), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("cert_fingerprint", sa.String(64), unique=True, nullable=True),
        sa.Column("cert_serial", sa.String(64), nullable=True),
        sa.Column("enrollment_token_hash", sa.String(128), nullable=True),
        sa.Column("enrollment_token_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enrollment_used", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ip", sa.String(45), nullable=True),
        sa.Column(
            "allowed_tools",
            sa.JSON(),
            nullable=False,
            server_default='["nmap","oradad","ad_collector"]',
        ),
        sa.Column("os_info", sa.String(255), nullable=True),
        sa.Column("agent_version", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agents_user_id", "agents", ["user_id"])

    # Creer la table agent_tasks
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_uuid", sa.String(36), unique=True, nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("audit_id", sa.Integer(), sa.ForeignKey("audits.id"), nullable=True),
        sa.Column("tool", sa.String(50), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status_message", sa.String(500), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("result_raw", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_tasks_agent_id", "agent_tasks", ["agent_id"])
    op.create_index("ix_agent_tasks_owner_id", "agent_tasks", ["owner_id"])
    op.create_index("ix_agent_tasks_audit_id", "agent_tasks", ["audit_id"])


def downgrade() -> None:
    op.drop_table("agent_tasks")
    op.drop_table("agents")
