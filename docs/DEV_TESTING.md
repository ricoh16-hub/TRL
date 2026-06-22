# Developer Testing (Local)

This project prefers PostgreSQL in CI and production. Use the steps below to run tests locally.

## Option A — Run tests with a local Postgres (recommended)

Prerequisites: `psql` client or Docker.

1. Start a Postgres container (Docker):

```sh
docker run --name trl-test-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=gbr -d -p 5432:5432 postgres:15
```

2. Create a dedicated app user and grant privileges:

```sh
psql -h localhost -U postgres -d gbr -c "CREATE USER app_client WITH PASSWORD 'test_password';"
psql -h localhost -U postgres -d gbr -c "GRANT ALL PRIVILEGES ON DATABASE gbr TO app_client;"
```

3. Export `DATABASE_URL` for tests:

```sh
# Linux/macOS
export DATABASE_URL=postgresql+psycopg2://app_client:test_password@localhost:5432/gbr
# Windows (cmd)
set DATABASE_URL=postgresql+psycopg2://app_client:test_password@localhost:5432/gbr
```

4. Run tests:

```sh
python -m pytest -q
```

## Option B — Quick local UI/testing using SQLite (developer opt-in)

For quick UI/debug runs you can opt in to using SQLite locally. This is NOT recommended for CI or production.

```sh
# Windows (cmd)
set ALLOW_SQLITE_DEV=1
# or PowerShell
$env:ALLOW_SQLITE_DEV = '1'
python -m pytest -q
```

If you want to run the application directly with a local SQLite file, set `DATABASE_URL` too:

```powershell
$env:ALLOW_SQLITE_DEV = '1'
$env:DATABASE_URL = 'sqlite:///./dev.db'
python src/main.py
```

Notes:
- Postgres-specific environment variables such as `DB_CONNECT_TIMEOUT` and `DB_SSLMODE` are
	ignored for SQLite; the code intentionally avoids passing Postgres-only `connect_args` to
	the SQLite DBAPI.

## Notes

- Do not commit `.env` with secrets. Use `.env.example` as a template.
- CI is configured to run tests against PostgreSQL via GitHub Actions (`.github/workflows/ci.yml`).
