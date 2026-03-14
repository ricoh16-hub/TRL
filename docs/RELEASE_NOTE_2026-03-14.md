# Release Note - 2026-03-14

## Summary

This update finalizes PostgreSQL-only operation and stabilizes Alembic execution from both CLI and VS Code tasks.

## Included Changes

1. Removed residual SQLite-related artifacts from workspace cleanup path.
2. Fixed Alembic wrapper execution to avoid local module path collision.
3. Updated VS Code Alembic tasks to run with workspace virtual environment interpreter.
4. Added operational handoff document for implementation and verification details.

## Verification

1. Alembic current revision: `20260313_02 (head)`
2. Alembic upgrade to head: success, no pending schema changes.
3. SQLite scan in project files (excluding `.venv` and caches): no references found.
4. SQLite file scan (`*.db`, `*.sqlite`, `*.sqlite3`): no files found.

## Commits

- `9efbedb` - fix alembic wrapper invocation
- `5cf0225` - use workspace venv for alembic tasks
- `eb3498e` - docs: add handoff notes for sqlite cleanup and alembic fixes

## Operational Notes

- Existing local edits in unrelated files remain untouched and are not included in these commits.
- VS Code tasks now run Alembic with `${workspaceFolder}\\.venv\\Scripts\\python.exe`.
