"""Add vlan_definitions table for site-scoped VLAN management.

Each site can define VLANs (id, name, subnet, color) that can be assigned
to equipment ports as untagged or tagged VLANs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_add_vlan_definitions"
down_revision: Union[str, None] = "005_move_ports_status_to_base"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vlan_definitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id"), nullable=False, index=True),
        sa.Column("vlan_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("subnet", sa.String(50), nullable=True),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6b7280"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("site_id", "vlan_id", name="uq_site_vlan_id"),
    )


def downgrade() -> None:
    op.drop_table("vlan_definitions")
