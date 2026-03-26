"""add_owner_id_and_encryption_columns

Revision ID: 553fec46eb0a
Revises: 6e27188411e6
Create Date: 2026-03-26 16:56:59.464200

Adds owner_id (nullable) to audits, scans_reseau, ad_audit_results.
Adds envelope encryption columns to attachments.
Converts ad_audit_results.username (VARCHAR->TEXT) and findings (JSON->TEXT)
for EncryptedText support. Existing data remains as-is (passthrough in dev mode).

Uses batch_alter_table for SQLite compatibility (FK constraints).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '553fec46eb0a'
down_revision: Union[str, None] = '6e27188411e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- audits: add owner_id ---
    with op.batch_alter_table("audits") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_audits_owner_id", ["owner_id"])
        batch_op.create_foreign_key(
            "fk_audits_owner_id", "users", ["owner_id"], ["id"]
        )

    # --- attachments: add envelope encryption columns ---
    with op.batch_alter_table("attachments") as batch_op:
        batch_op.add_column(sa.Column("file_uuid", sa.String(36), nullable=True))
        batch_op.create_unique_constraint("uq_attachments_file_uuid", ["file_uuid"])
        batch_op.add_column(
            sa.Column("encrypted_dek", sa.LargeBinary(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("dek_nonce", sa.LargeBinary(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("kek_version", sa.Integer(), nullable=True, server_default="1")
        )

    # --- scans_reseau: add owner_id ---
    # Note: raw_xml_output reste TEXT en base — EncryptedText est un TypeDecorator
    # applicatif, pas un changement de type SQL.
    with op.batch_alter_table("scans_reseau") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_scans_reseau_owner_id", ["owner_id"])
        batch_op.create_foreign_key(
            "fk_scans_reseau_owner_id", "users", ["owner_id"], ["id"]
        )

    # --- ad_audit_results: add owner_id + type changes ---
    with op.batch_alter_table("ad_audit_results") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_ad_audit_results_owner_id", ["owner_id"])
        batch_op.create_foreign_key(
            "fk_ad_audit_results_owner_id", "users", ["owner_id"], ["id"]
        )
        # username VARCHAR(255) -> TEXT (EncryptedText stores hex, can exceed 255)
        batch_op.alter_column(
            "username",
            existing_type=sa.String(255),
            type_=sa.Text(),
            existing_nullable=False,
        )
        # findings JSON -> TEXT (EncryptedText)
        # On SQLite, JSON is stored as TEXT natively — no data loss.
        # On PostgreSQL, use CAST via postgresql_using.
        batch_op.alter_column(
            "findings",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    # --- ad_audit_results: revert ---
    with op.batch_alter_table("ad_audit_results") as batch_op:
        batch_op.alter_column(
            "findings",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "username",
            existing_type=sa.Text(),
            type_=sa.String(255),
            existing_nullable=False,
        )
        batch_op.drop_constraint("fk_ad_audit_results_owner_id", type_="foreignkey")
        batch_op.drop_index("ix_ad_audit_results_owner_id")
        batch_op.drop_column("owner_id")

    # --- scans_reseau: revert ---
    with op.batch_alter_table("scans_reseau") as batch_op:
        batch_op.drop_constraint("fk_scans_reseau_owner_id", type_="foreignkey")
        batch_op.drop_index("ix_scans_reseau_owner_id")
        batch_op.drop_column("owner_id")

    # --- attachments: revert ---
    with op.batch_alter_table("attachments") as batch_op:
        batch_op.drop_column("kek_version")
        batch_op.drop_column("dek_nonce")
        batch_op.drop_column("encrypted_dek")
        batch_op.drop_constraint("uq_attachments_file_uuid", type_="unique")
        batch_op.drop_column("file_uuid")

    # --- audits: revert ---
    with op.batch_alter_table("audits") as batch_op:
        batch_op.drop_constraint("fk_audits_owner_id", type_="foreignkey")
        batch_op.drop_index("ix_audits_owner_id")
        batch_op.drop_column("owner_id")
