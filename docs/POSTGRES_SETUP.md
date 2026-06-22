# PostgreSQL Setup and Deployment Guide

This guide explains how to provision a PostgreSQL database for this application and configure environment variables.

## 1. Create a database and user (local Postgres)

Run the following in a shell where `psql` is available and you're a Postgres superuser:

```sh
# create DB
psql -c "CREATE DATABASE gbr;"
# create user
psql -c "CREATE USER app_client WITH PASSWORD 'change_me_strong_password';"
# grant privileges
psql -c "GRANT ALL PRIVILEGES ON DATABASE gbr TO app_client;"
```

## 2. Example env variables

Create a `.env` file (do NOT commit) by copying `.env.example` and filling values:

```
DB_USER=app_client
DB_PASSWORD=your_strong_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gbr
DB_CONNECT_TIMEOUT=10
DB_APP_NAME=python-apps-12R
DB_AUTO_MIGRATE=0
DB_CENTRAL_MODE=0
DB_CENTRAL_REQUIRE_SSL=1
```

Alternatively set a full `DATABASE_URL` (recommended when password contains special chars):

```
DATABASE_URL=postgresql+psycopg2://app_client:your%40password@db-host:5432/gbr
```

Note: when using `DATABASE_URL`, it must point to a PostgreSQL server (sqlite is not supported).

## 3. Running migrations

By default automatic migrations are disabled for non-owner users. To run migrations explicitly:

```sh
# as admin/owner
export DB_AUTO_MIGRATE=1
python scripts/alembic_cli.py upgrade head
```

If using the built-in migrator, prefer running as a DB owner or use Alembic CLI for controlled migrations.

## 4. CI / Deployment

- Provide `DATABASE_URL` via your CI secrets or platform environment variables.
- Ensure `DB_AUTO_MIGRATE=0` in production and run migrations via an admin job.
- Use TLS (set `DB_SSLMODE=require|verify-ca|verify-full`) when connecting to managed DBs.

## 5. Troubleshooting

- `Connection refused` — check the host/port and that Postgres is running and listening.
- `password authentication failed` — verify username/password and prefer `DATABASE_URL` if password contains special characters.
- If you need local development with SQLite for quick UI tests, use a separate developer branch and set `DATABASE_URL=sqlite:///./dev.db` locally (note: not supported by main branch).