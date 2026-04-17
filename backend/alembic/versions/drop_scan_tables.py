"""drop_scan_tables

Revision ID: drop_scan_tables
Revises: 8cd801626d19
Create Date: 2026-04-17

Supprime les tables du scanner nmap local (scans_reseau, scan_hosts, scan_ports).
Le scan nmap est désormais délégué à l'agent distant via AgentTask — les
résultats sont consommés directement par le pipeline de collecte.

Ordre de drop respectant les FK : scan_ports → scan_hosts → scans_reseau.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "drop_scan_tables"
down_revision: Union[str, None] = "8cd801626d19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = __import__("sqlalchemy").inspect(bind)
    existing = set(inspector.get_table_names())
    for table in ("scan_ports", "scan_hosts", "scans_reseau"):
        if table in existing:
            op.drop_table(table)


def downgrade() -> None:
    # Downgrade volontairement non implémenté : la feature est supprimée
    # et les modèles SQLAlchemy correspondants n'existent plus.
    raise NotImplementedError(
        "drop_scan_tables: downgrade non supporté — la feature a été retirée."
    )
