"""
Reset a local user password (admin by default).

Usage:
    python reset_admin_password.py
    python reset_admin_password.py --username admin --password "NewStrongPass@2026"
"""

import argparse
import io
import sys
from pathlib import Path

# Force UTF-8 console output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add backend folder to import path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402


def reset_password(username: str, new_password: str) -> int:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"[ERROR] User '{username}' not found")
            return 1

        user.password_hash = hash_password(new_password)
        db.commit()
        print(f"[OK] Password updated for '{username}'")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset local AssistantAudit user password")
    parser.add_argument("--username", default="admin", help="Username to update (default: admin)")
    parser.add_argument(
        "--password",
        default="Admin@2026!",
        help="New password to set (default: Admin@2026!)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("AssistantAudit - Password Reset")
    print("=" * 60)
    print(f"Username: {args.username}")

    rc = reset_password(args.username, args.password)
    if rc == 0:
        print("[INFO] You can now log in with the new password")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
