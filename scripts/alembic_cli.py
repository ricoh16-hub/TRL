from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Helper CLI untuk workflow Alembic.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    current_parser = subparsers.add_parser("current", help="Tampilkan revision Alembic aktif")
    add_admin_options(current_parser)

    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade schema ke revision tertentu")
    upgrade_parser.add_argument("revision", nargs="?", default="head")
    add_admin_options(upgrade_parser)

    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade schema ke revision tertentu")
    downgrade_parser.add_argument("revision", nargs="?", default="-1")
    add_admin_options(downgrade_parser)

    revision_parser = subparsers.add_parser("revision", help="Buat revision Alembic baru")
    revision_parser.add_argument("-m", "--message", required=True)
    revision_parser.add_argument("--autogenerate", action="store_true")
    revision_parser.add_argument("--safe", action="store_true")
    add_admin_options(revision_parser)

    return parser


def add_admin_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--admin-user", default="")
    parser.add_argument("--admin-password", default="")


def resolve_admin_password(admin_user: str, admin_password: str) -> str:
    if not admin_user:
        return admin_password

    if admin_password:
        return admin_password

    env_password = os.getenv("DB_ADMIN_PASSWORD", "")
    if env_password:
        return env_password

    return getpass.getpass("Masukkan DB admin password: ")


def run_alembic(command_args: list[str], admin_user: str = "", admin_password: str = "") -> None:
    env = os.environ.copy()
    if admin_user:
        env["DB_ADMIN_USER"] = admin_user

    resolved_password = resolve_admin_password(admin_user, admin_password)
    if resolved_password:
        env["DB_ADMIN_PASSWORD"] = resolved_password

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from alembic.config import main; main()",
            *command_args,
        ],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def print_safe_revision_hint() -> None:
    versions_dir = PROJECT_ROOT / "alembic" / "versions"
    latest_revision = None
    if versions_dir.exists():
        revision_files = [path for path in versions_dir.iterdir() if path.is_file()]
        if revision_files:
            latest_revision = max(revision_files, key=lambda item: item.stat().st_mtime)

    if latest_revision is not None:
        print(f"Revision terbaru: {latest_revision}")

    print()
    print("Checklist aman setelah membuat revision:")
    print("1. Review upgrade() dan downgrade().")
    print("2. Hindari operasi destructive dalam satu step bila bisa dibuat bertahap.")
    print("3. Untuk kolom NOT NULL: add nullable -> backfill -> set NOT NULL.")
    print("4. Jalankan alembic upgrade head di environment uji sebelum production.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "current":
        run_alembic(["current"], admin_user=args.admin_user, admin_password=args.admin_password)
        return

    if args.command == "upgrade":
        run_alembic(["upgrade", args.revision], admin_user=args.admin_user, admin_password=args.admin_password)
        return

    if args.command == "downgrade":
        run_alembic(["downgrade", args.revision], admin_user=args.admin_user, admin_password=args.admin_password)
        return

    if args.command == "revision":
        command_args = ["revision", "-m", args.message]
        if args.autogenerate:
            command_args.append("--autogenerate")

        run_alembic(command_args, admin_user=args.admin_user, admin_password=args.admin_password)
        if args.safe:
            print_safe_revision_hint()
        return

    raise SystemExit("Command Alembic tidak dikenali.")


if __name__ == "__main__":
    main()