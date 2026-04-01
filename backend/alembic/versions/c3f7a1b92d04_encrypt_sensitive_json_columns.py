"""encrypt sensitive json columns

Revision ID: c3f7a1b92d04
Revises: b8e4c3d91f02
Create Date: 2026-03-29 10:00:00.000000

Migre les colonnes sensibles vers des types chiffres :
- agent_tasks.parameters : JSON -> EncryptedJSON (Text)
- ad_audit_results.dc_list : JSON -> EncryptedJSON (Text)
- ad_audit_results.domain_admins : JSON -> EncryptedJSON (Text)
- collect_results.username : String(255) -> EncryptedText (Text)

Les donnees existantes sont converties : JSON est serialise en texte,
puis chiffre si ENCRYPTION_KEY est configuree.
"""
import json
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3f7a1b92d04'
down_revision: Union[str, None] = 'b8e4c3d91f02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_cipher():
    """Retourne le cipher AES-256-GCM si ENCRYPTION_KEY est configuree."""
    key = os.environ.get("ENCRYPTION_KEY", "")
    if not key:
        return None
    from app.core.encryption import AES256GCMCipher
    return AES256GCMCipher(key)


def _encrypt(cipher, value: str) -> str:
    """Chiffre une chaine si le cipher est disponible."""
    if cipher is None:
        return value
    return cipher.encrypt(value)


def _decrypt(cipher, value: str) -> str:
    """Dechiffre une chaine si le cipher est disponible."""
    if cipher is None:
        return value
    return cipher.decrypt(value)


def upgrade() -> None:
    cipher = _get_cipher()
    conn = op.get_bind()

    # ── agent_tasks.parameters : JSON -> Text (EncryptedJSON) ──
    # Lire les donnees existantes
    rows = conn.execute(sa.text("SELECT id, parameters FROM agent_tasks")).fetchall()

    # SQLite : recréer la colonne en Text via batch
    with op.batch_alter_table("agent_tasks") as batch_op:
        batch_op.alter_column(
            "parameters",
            type_=sa.Text(),
            existing_type=sa.JSON(),
            existing_nullable=False,
        )

    # Convertir les donnees existantes
    for row in rows:
        raw = row[1]
        if raw is None:
            continue
        # La valeur peut etre deja un dict (JSON natif) ou un string
        if isinstance(raw, (dict, list)):
            json_str = json.dumps(raw, ensure_ascii=False)
        else:
            json_str = str(raw)
        encrypted = _encrypt(cipher, json_str)
        conn.execute(
            sa.text("UPDATE agent_tasks SET parameters = :val WHERE id = :id"),
            {"val": encrypted, "id": row[0]},
        )

    # ── ad_audit_results.dc_list : JSON -> Text (EncryptedJSON) ──
    rows = conn.execute(
        sa.text("SELECT id, dc_list, domain_admins FROM ad_audit_results")
    ).fetchall()

    with op.batch_alter_table("ad_audit_results") as batch_op:
        batch_op.alter_column(
            "dc_list",
            type_=sa.Text(),
            existing_type=sa.JSON(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "domain_admins",
            type_=sa.Text(),
            existing_type=sa.JSON(),
            existing_nullable=True,
        )

    for row in rows:
        row_id = row[0]
        for col_idx, col_name in [(1, "dc_list"), (2, "domain_admins")]:
            raw = row[col_idx]
            if raw is None:
                continue
            if isinstance(raw, (dict, list)):
                json_str = json.dumps(raw, ensure_ascii=False)
            else:
                json_str = str(raw)
            encrypted = _encrypt(cipher, json_str)
            conn.execute(
                sa.text(f"UPDATE ad_audit_results SET {col_name} = :val WHERE id = :id"),
                {"val": encrypted, "id": row_id},
            )

    # ── collect_results.username : String(255) -> Text (EncryptedText) ──
    rows = conn.execute(
        sa.text("SELECT id, username FROM collect_results")
    ).fetchall()

    with op.batch_alter_table("collect_results") as batch_op:
        batch_op.alter_column(
            "username",
            type_=sa.Text(),
            existing_type=sa.String(255),
            existing_nullable=False,
        )

    for row in rows:
        if row[1] is None:
            continue
        encrypted = _encrypt(cipher, row[1])
        conn.execute(
            sa.text("UPDATE collect_results SET username = :val WHERE id = :id"),
            {"val": encrypted, "id": row[0]},
        )


def downgrade() -> None:
    cipher = _get_cipher()
    conn = op.get_bind()

    # ── collect_results.username : Text -> String(255) ──
    rows = conn.execute(
        sa.text("SELECT id, username FROM collect_results")
    ).fetchall()

    for row in rows:
        if row[1] is None:
            continue
        decrypted = _decrypt(cipher, row[1])
        conn.execute(
            sa.text("UPDATE collect_results SET username = :val WHERE id = :id"),
            {"val": decrypted, "id": row[0]},
        )

    with op.batch_alter_table("collect_results") as batch_op:
        batch_op.alter_column(
            "username",
            type_=sa.String(255),
            existing_type=sa.Text(),
            existing_nullable=False,
        )

    # ── ad_audit_results.dc_list, domain_admins : Text -> JSON ──
    rows = conn.execute(
        sa.text("SELECT id, dc_list, domain_admins FROM ad_audit_results")
    ).fetchall()

    for row in rows:
        row_id = row[0]
        for col_idx, col_name in [(1, "dc_list"), (2, "domain_admins")]:
            raw = row[col_idx]
            if raw is None:
                continue
            decrypted = _decrypt(cipher, raw)
            parsed = json.loads(decrypted)
            conn.execute(
                sa.text(f"UPDATE ad_audit_results SET {col_name} = :val WHERE id = :id"),
                {"val": json.dumps(parsed), "id": row_id},
            )

    with op.batch_alter_table("ad_audit_results") as batch_op:
        batch_op.alter_column(
            "dc_list",
            type_=sa.JSON(),
            existing_type=sa.Text(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "domain_admins",
            type_=sa.JSON(),
            existing_type=sa.Text(),
            existing_nullable=True,
        )

    # ── agent_tasks.parameters : Text -> JSON ──
    rows = conn.execute(
        sa.text("SELECT id, parameters FROM agent_tasks")
    ).fetchall()

    for row in rows:
        if row[1] is None:
            continue
        decrypted = _decrypt(cipher, row[1])
        parsed = json.loads(decrypted)
        conn.execute(
            sa.text("UPDATE agent_tasks SET parameters = :val WHERE id = :id"),
            {"val": json.dumps(parsed), "id": row[0]},
        )

    with op.batch_alter_table("agent_tasks") as batch_op:
        batch_op.alter_column(
            "parameters",
            type_=sa.JSON(),
            existing_type=sa.Text(),
            existing_nullable=False,
        )
