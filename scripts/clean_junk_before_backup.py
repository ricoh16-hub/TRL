"""Clean local junk files before creating a project backup.

The default mode is a dry run. Pass --apply to delete the reported files.
"""

from __future__ import annotations

import argparse
import fnmatch
import shutil
from dataclasses import dataclass
from pathlib import Path


SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "backup",
    "backups",
    "assets",
    "alembic",
}

JUNK_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".hypothesis",
    "htmlcov",
    "build",
    "dist",
}

JUNK_DIR_PATTERNS = (
    "pytest-cache-files-*",
    "*.egg-info",
)

JUNK_FILE_PATTERNS = (
    "*.pyc",
    "*.pyo",
    "*.tmp",
    "*.temp",
    ".coverage",
    "coverage.xml",
)

DEBUG_FILE_NAMES = {
    "db_info.txt",
    "wifi_debug.txt",
}


@dataclass(frozen=True)
class CleanupTarget:
    path: Path
    kind: str
    size: int
    reason: str


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
    except ValueError:
        return False
    return True


def _safe_target(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if resolved == root or not _is_relative_to(resolved, root):
        raise ValueError(f"Refusing to touch path outside workspace: {path}")
    return resolved


def _matches_any(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def _safe_size(path: Path) -> int:
    try:
        if path.is_file() or path.is_symlink():
            return path.stat().st_size
        total = 0
        for child in path.rglob("*"):
            try:
                if child.is_file() or child.is_symlink():
                    total += child.stat().st_size
            except OSError:
                continue
        return total
    except OSError:
        return 0


def _collect_targets(root: Path, include_debug: bool) -> list[CleanupTarget]:
    targets: list[CleanupTarget] = []

    def walk(directory: Path) -> None:
        try:
            entries = list(directory.iterdir())
        except OSError as exc:
            print(f"SKIP unreadable: {directory.relative_to(root)} ({exc.strerror or exc})")
            return

        for entry in entries:
            name = entry.name
            if entry.is_dir():
                if name in SKIP_DIR_NAMES:
                    continue
                if name in JUNK_DIR_NAMES or _matches_any(name, JUNK_DIR_PATTERNS):
                    safe = _safe_target(entry, root)
                    targets.append(
                        CleanupTarget(
                            path=safe,
                            kind="dir",
                            size=_safe_size(safe),
                            reason="cache/build artifact",
                        )
                    )
                    continue
                walk(entry)
                continue

            if name in DEBUG_FILE_NAMES and include_debug:
                safe = _safe_target(entry, root)
                targets.append(
                    CleanupTarget(
                        path=safe,
                        kind="file",
                        size=_safe_size(safe),
                        reason="local debug output",
                    )
                )
                continue

            if _matches_any(name, JUNK_FILE_PATTERNS):
                safe = _safe_target(entry, root)
                targets.append(
                    CleanupTarget(
                        path=safe,
                        kind="file",
                        size=_safe_size(safe),
                        reason="temporary/test artifact",
                    )
                )

    walk(root)
    return sorted(targets, key=lambda item: str(item.path).lower())


def _format_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    if size >= 1024:
        return f"{size / 1024:.2f} KB"
    return f"{size} B"


def _delete_target(target: CleanupTarget) -> None:
    if target.kind == "dir":
        shutil.rmtree(target.path)
    else:
        target.path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean safe local junk files before backup. Dry-run by default."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete the reported junk files and directories.",
    )
    parser.add_argument(
        "--include-debug",
        action="store_true",
        help="Also delete root debug files such as db_info.txt and wifi_debug.txt.",
    )
    args = parser.parse_args()

    root = _workspace_root()
    targets = _collect_targets(root, include_debug=args.include_debug)
    total_size = sum(target.size for target in targets)

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"{mode}: workspace={root}")
    print(f"Targets: {len(targets)} item(s), {_format_size(total_size)}")

    for target in targets:
        relative = target.path.relative_to(root)
        print(f"- {target.kind:4} {_format_size(target.size):>10} {relative} [{target.reason}]")

    if not args.apply:
        print("No files were deleted. Re-run with --apply to clean before backup.")
        return 0

    failures = 0
    for target in targets:
        try:
            _delete_target(target)
        except OSError as exc:
            failures += 1
            print(f"FAILED: {target.path.relative_to(root)} ({exc})")

    deleted = len(targets) - failures
    print(f"Deleted: {deleted} item(s). Failed: {failures}.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
