# Push Checklist - 2026-03-14

## Current Status

- Branch: master
- Working tree: clean
- Remote: not configured
- Alembic current: 20260313_02 (head)

## Commits To Push (latest first)

- 86ebf08 chore: update latest wifi diagnostics snapshot
- 07d4394 chore: refine password reset script env write and linter signal
- a7fee6c docs: normalize markdown formatting in final README
- a081281 docs: add release note for postgres and alembic stabilization
- eb3498e docs: add handoff notes for sqlite cleanup and alembic fixes
- 5cf0225 use workspace venv for alembic tasks
- 9efbedb fix alembic wrapper invocation

## Commands

1. Add remote

git remote add origin <REMOTE_URL>

2. Verify remote

git remote -v

3. Push branch

git push -u origin master

4. Verify branch tracking

git branch -vv

## Optional

- If default branch in remote is main, rename local branch before push:

git branch -M main
git push -u origin main
