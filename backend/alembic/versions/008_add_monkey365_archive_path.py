"""Add archive_path column to monkey365_scan_results.

Stores the path where Monkey365 reports are archived after scan completion
(e.g., /data/enterprise/Cloud/M365/{scan_id}).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_add_monkey365_archive_path"
down_revision: Union[str, None] = "007_add_monkey365_scan_results"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("monkey365_scan_results")]

    if "archive_path" not in columns:
        op.add_column(
            "monkey365_scan_results",
            sa.Column("archive_path", sa.String(500), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("monkey365_scan_results", "archive_path")
