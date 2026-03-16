from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_add_network_map_tables"
down_revision: Union[str, None] = "001_add_source_author"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("network_links"):
        op.create_table(
            "network_links",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("site_id", sa.Integer(), nullable=False),
            sa.Column("source_equipement_id", sa.Integer(), nullable=False),
            sa.Column("target_equipement_id", sa.Integer(), nullable=False),
            sa.Column("source_interface", sa.String(length=100), nullable=True),
            sa.Column("target_interface", sa.String(length=100), nullable=True),
            sa.Column("link_type", sa.String(length=50), nullable=False),
            sa.Column("bandwidth", sa.String(length=50), nullable=True),
            sa.Column("vlan", sa.String(length=100), nullable=True),
            sa.Column("network_segment", sa.String(length=100), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
            sa.ForeignKeyConstraint(["source_equipement_id"], ["equipements.id"]),
            sa.ForeignKeyConstraint(["target_equipement_id"], ["equipements.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "source_equipement_id",
                "target_equipement_id",
                "source_interface",
                "target_interface",
                name="uq_network_link_pair",
            ),
        )
        op.create_index(op.f("ix_network_links_site_id"), "network_links", ["site_id"], unique=False)
        op.create_index(op.f("ix_network_links_source_equipement_id"), "network_links", ["source_equipement_id"], unique=False)
        op.create_index(op.f("ix_network_links_target_equipement_id"), "network_links", ["target_equipement_id"], unique=False)

    if not _table_exists("network_map_layouts"):
        op.create_table(
            "network_map_layouts",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("site_id", sa.Integer(), nullable=False),
            sa.Column("layout_data", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("site_id"),
        )
        op.create_index(op.f("ix_network_map_layouts_site_id"), "network_map_layouts", ["site_id"], unique=True)

    if not _table_exists("site_connections"):
        op.create_table(
            "site_connections",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("entreprise_id", sa.Integer(), nullable=False),
            sa.Column("source_site_id", sa.Integer(), nullable=False),
            sa.Column("target_site_id", sa.Integer(), nullable=False),
            sa.Column("link_type", sa.String(length=50), nullable=False),
            sa.Column("bandwidth", sa.String(length=50), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["entreprise_id"], ["entreprises.id"]),
            sa.ForeignKeyConstraint(["source_site_id"], ["sites.id"]),
            sa.ForeignKeyConstraint(["target_site_id"], ["sites.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "entreprise_id",
                "source_site_id",
                "target_site_id",
                "link_type",
                name="uq_site_connection_pair",
            ),
        )
        op.create_index(op.f("ix_site_connections_entreprise_id"), "site_connections", ["entreprise_id"], unique=False)
        op.create_index(op.f("ix_site_connections_source_site_id"), "site_connections", ["source_site_id"], unique=False)
        op.create_index(op.f("ix_site_connections_target_site_id"), "site_connections", ["target_site_id"], unique=False)


def downgrade() -> None:
    if _table_exists("site_connections"):
        op.drop_index(op.f("ix_site_connections_target_site_id"), table_name="site_connections")
        op.drop_index(op.f("ix_site_connections_source_site_id"), table_name="site_connections")
        op.drop_index(op.f("ix_site_connections_entreprise_id"), table_name="site_connections")
        op.drop_table("site_connections")

    if _table_exists("network_map_layouts"):
        op.drop_index(op.f("ix_network_map_layouts_site_id"), table_name="network_map_layouts")
        op.drop_table("network_map_layouts")

    if _table_exists("network_links"):
        op.drop_index(op.f("ix_network_links_target_equipement_id"), table_name="network_links")
        op.drop_index(op.f("ix_network_links_source_equipement_id"), table_name="network_links")
        op.drop_index(op.f("ix_network_links_site_id"), table_name="network_links")
        op.drop_table("network_links")
