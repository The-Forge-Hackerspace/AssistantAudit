"""
Migration: Add missing columns to monkey365_scan_results table.

Adds: auth_mode, force_msal_desktop, powershell_config, archive_path
Each ALTER TABLE is idempotent — silently skips columns that already exist.
"""

import sqlite3
import sys
from pathlib import Path

# Resolve DB path from config (same logic as Settings.DATABASE_URL)
BASE_DIR = Path(__file__).resolve().parent / "app"
DB_PATH = Path(__file__).resolve().parent / "instance" / "assistantaudit.db"

MIGRATIONS = [
    ("auth_mode", "ALTER TABLE monkey365_scan_results ADD COLUMN auth_mode VARCHAR(50)"),
    (
        "force_msal_desktop",
        "ALTER TABLE monkey365_scan_results ADD COLUMN force_msal_desktop BOOLEAN NOT NULL DEFAULT 0",
    ),
    ("powershell_config", "ALTER TABLE monkey365_scan_results ADD COLUMN powershell_config JSON"),
    ("archive_path", "ALTER TABLE monkey365_scan_results ADD COLUMN archive_path VARCHAR(500)"),
]


def get_existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def run_migration() -> None:
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found at: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Connecting to: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    try:
        existing = get_existing_columns(conn, "monkey365_scan_results")
        print(f"[INFO] Existing columns: {sorted(existing)}\n")

        added = []
        skipped = []

        for col_name, sql in MIGRATIONS:
            if col_name in existing:
                print(f"[SKIP] '{col_name}' already exists — no change needed.")
                skipped.append(col_name)
            else:
                try:
                    conn.execute(sql)
                    conn.commit()
                    print(f"[ADDED] '{col_name}' — column added successfully.")
                    added.append(col_name)
                except sqlite3.OperationalError as e:
                    print(f"[ERROR] Failed to add '{col_name}': {e}", file=sys.stderr)
                    conn.rollback()
                    sys.exit(1)

        print(f"\n[DONE] Added: {added or 'none'} | Skipped (already present): {skipped or 'none'}")

        # Final verification
        final_cols = get_existing_columns(conn, "monkey365_scan_results")
        expected = {col for col, _ in MIGRATIONS}
        missing = expected - final_cols
        if missing:
            print(f"[WARN] Still missing after migration: {missing}", file=sys.stderr)
            sys.exit(1)
        else:
            print("[OK] All 4 target columns are present in the table.")
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
