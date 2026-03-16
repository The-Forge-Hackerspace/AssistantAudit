"""Move ports_status from equipements_reseau to base equipements table.

All equipment types can now have port configurations, not just network devices.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_move_ports_status_to_base"
down_revision: Union[str, None] = "004_migrate_switch_router_ap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add ports_status column to base equipements table
    op.add_column("equipements", sa.Column("ports_status", sa.JSON(), nullable=True))

    # 2. Migrate existing ports_status data from equipements_reseau to equipements
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE equipements SET ports_status = ("
            "  SELECT er.ports_status FROM equipements_reseau er"
            "  WHERE er.id = equipements.id"
            ") WHERE id IN (SELECT id FROM equipements_reseau WHERE ports_status IS NOT NULL)"
        )
    )

    # 3. Drop ports_status column from equipements_reseau
    #    SQLite doesn't support DROP COLUMN before 3.35.0, use batch mode
    with op.batch_alter_table("equipements_reseau") as batch_op:
        batch_op.drop_column("ports_status")


def downgrade() -> None:
    # 1. Re-add ports_status to equipements_reseau
    with op.batch_alter_table("equipements_reseau") as batch_op:
        batch_op.add_column(sa.Column("ports_status", sa.JSON(), nullable=True))

    # 2. Copy data back from equipements to equipements_reseau
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE equipements_reseau SET ports_status = ("
            "  SELECT e.ports_status FROM equipements e"
            "  WHERE e.id = equipements_reseau.id"
            ") WHERE id IN (SELECT id FROM equipements WHERE ports_status IS NOT NULL)"
        )
    )

    # 3. Drop ports_status from equipements
    with op.batch_alter_table("equipements") as batch_op:
        batch_op.drop_column("ports_status")
