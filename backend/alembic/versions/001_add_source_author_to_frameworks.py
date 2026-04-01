"""Add source and author columns to frameworks

Revision ID: 001_add_source_author
Revises: None
Create Date: 2026-03-14
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_add_source_author"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Vérifie si une colonne existe déjà (compatible SQLite et PostgreSQL)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    if not _column_exists("frameworks", "source"):
        op.add_column("frameworks", sa.Column("source", sa.String(500), nullable=True))
    if not _column_exists("frameworks", "author"):
        op.add_column("frameworks", sa.Column("author", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("frameworks", "author")
    op.drop_column("frameworks", "source")
