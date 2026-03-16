"""Migrate switch/router/access_point to equipements_reseau table.

These types now inherit from EquipementReseau (joined-table inheritance)
instead of bare Equipement, so they need rows in equipements_reseau.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_migrate_switch_router_ap"
down_revision: Union[str, None] = "003_drop_network_link_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # For each existing switch/router/access_point in equipements table,
    # insert a corresponding row in equipements_reseau (joined-table inheritance).
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT id FROM equipements "
            "WHERE type_equipement IN ('switch', 'router', 'access_point') "
            "AND id NOT IN (SELECT id FROM equipements_reseau)"
        )
    )
    ids = [row[0] for row in result]
    for eq_id in ids:
        conn.execute(
            sa.text(
                "INSERT INTO equipements_reseau (id) VALUES (:id)"
            ),
            {"id": eq_id},
        )


def downgrade() -> None:
    # Remove the equipements_reseau rows for switch/router/access_point
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM equipements_reseau "
            "WHERE id IN ("
            "  SELECT id FROM equipements "
            "  WHERE type_equipement IN ('switch', 'router', 'access_point')"
            ")"
        )
    )
