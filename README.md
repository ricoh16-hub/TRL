# README

## Deskripsi

Aplikasi ini adalah aplikasi Python yang telah dioptimalkan dan dibersihkan dari file tidak penting.

## Cara Menjalankan

1. Pastikan Python 3.10+ sudah terinstall.

2. Buat dan aktifkan virtual environment di root project.

   PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependensi runtime yang sudah dipin:

   ```bash
   python -m pip install -r requirements.txt
   ```

   Untuk mesin pengembangan, install juga dependency dev:

   ```bash
   python -m pip install -r requirements-dev.txt
   ```

4. Siapkan PostgreSQL dan buat database, misalnya `GBR`.

5. Set koneksi PostgreSQL.

   Best practice: pakai user database aplikasi khusus, bukan `postgres`.

   Disarankan pakai variable terpisah (lebih aman):

   ```powershell
   $env:DB_USER = "app_client"
   $env:DB_PASSWORD = "PASSWORD_APP_DB_ANDA"
   $env:DB_HOST = "localhost"
   $env:DB_PORT = "5432"
   $env:DB_NAME = "GBR"
   $env:DB_CONNECT_TIMEOUT = "10"
   $env:DB_APP_NAME = "python-apps-12R"
   ```

   Alternatif (single URL):

   ```powershell
   $env:DATABASE_URL = "postgresql+psycopg2://app_client:PASSWORD_APP_DB_ANDA@localhost:5432/GBR"
   ```

   Atau gunakan file `.env`:

   - Copy `.env.example` menjadi `.env`
   - Isi `DB_PASSWORD` dengan password app DB user yang benar

6. Jalankan aplikasi:

   ```bash
   python src/main.py
   ```

Catatan:

- `requirements.txt` berisi versi exact yang sudah tervalidasi di workspace ini agar lingkungan mesin lain tidak berubah otomatis.
- `requirements-dev.txt` dipakai untuk kebutuhan pengembangan dan saat ini menambahkan `pytest` serta `ruff` dengan versi yang dipin.

## Tooling Pengembangan

- Jalankan lint dengan `python -m ruff check src/auth src/database src/main.py src/ui/mainform.py src/ui/userform.py src/ui/webform.py src/ui/battery_status.py src/ui/boot.py src/ui/login.py src/ui/lock.py scripts tests`.
- Jalankan test dengan `python -m pytest`.
- Test sekarang otomatis mengeluarkan report coverage terminal dan file `coverage.xml`.
- VS Code task siap pakai: `Python Lint (Ruff)`, `Python Tests (Pytest)`, `Python Tests (Coverage)`, `Python Verify`, dan `Python Verify (With Coverage)`.
- CI GitHub menjalankan lint dan test yang sama pada setiap `push` dan `pull_request`.
- Scope lint sekarang sudah mencakup modul UI utama yang aktif dipakai aplikasi. Jika ada file backup/legacy lain di luar scope ini, pertahankan terpisah sampai benar-benar siap dirapikan.

## Koneksi Database (Multi User)

- Aplikasi sekarang menggunakan PostgreSQL melalui SQLAlchemy.
- Connection pooling aktif (pool size 10, max overflow 20, pre-ping aktif) agar aman untuk akses concurrent/multi-user.
- Tabel akan diinisialisasi otomatis saat startup aplikasi.
- File `.env` dibaca relatif dari root project, jadi tidak tergantung current working directory.
- Gunakan role DB non-superuser dengan privilege minimum untuk runtime aplikasi.
- Runtime aplikasi tidak disarankan menjalankan DDL otomatis. Gunakan migrasi admin terpisah untuk perubahan schema.

### Mode Database Terpusat (Direkomendasikan)

- Aktifkan `DB_CENTRAL_MODE=1` di `.env`.
- Isi `DB_HOST` dengan IP/hostname server PostgreSQL terpusat (jangan `localhost`).
- Pastikan `DB_AUTO_MIGRATE=0` untuk runtime client.
- Aktifkan TLS koneksi dengan `DB_SSLMODE=require` (atau `verify-ca`/`verify-full`).
- Saat `DB_CENTRAL_MODE=1`, startup aplikasi akan memvalidasi host bukan local loopback, auto-migrate runtime nonaktif, dan mode SSL sesuai policy.

- Checklist operasional lengkap: [docs/CENTRALIZED_POSTGRESQL_CHECKLIST.md](docs/CENTRALIZED_POSTGRESQL_CHECKLIST.md)

## Operasional yang Disarankan

- Provision / perbarui user aplikasi: [scripts/provision_app_db_user.py](scripts/provision_app_db_user.py)
- Rotasi password user aplikasi: [scripts/rotate_app_db_password.py](scripts/rotate_app_db_password.py)
- Migrasi schema password user lama: [scripts/migrate_user_password_schema.py](scripts/migrate_user_password_schema.py)
- Reset password admin PostgreSQL lokal: [scripts/reset_postgres_password_admin.ps1](scripts/reset_postgres_password_admin.ps1)
- Simpan `.env` hanya di mesin lokal / secret store. File ini sudah di-ignore oleh Git.

## Alembic Migration Workflow

- Baseline / apply migration ke head:

   ```powershell
   $env:DB_ADMIN_USER = "postgres"
   $env:DB_ADMIN_PASSWORD = "PASSWORD_ADMIN_DB"
   python -m alembic upgrade head
   ```

- Cek revision aktif:

   ```powershell
   python -m alembic current
   ```

- Buat revision baru untuk perubahan schema berikutnya:

   ```powershell
   python -m alembic revision -m "deskripsi_perubahan_schema"
   ```

- Untuk migrasi schema, gunakan kredensial admin/owner schema. Runtime app tetap memakai user `app_client`.
- Revision aktif saat ini: `20260313_02 (head)`.
- Contoh revision riil yang sudah diterapkan: [alembic/versions/20260313_02_add_user_audit_timestamps.py](alembic/versions/20260313_02_add_user_audit_timestamps.py)
- Helper CLI migrasi tersedia di [scripts/alembic_cli.py](scripts/alembic_cli.py).
- Contoh penggunaan:

   ```powershell
   python scripts/alembic_cli.py current --admin-user postgres
   python scripts/alembic_cli.py upgrade head --admin-user postgres
   python scripts/alembic_cli.py downgrade -1 --admin-user postgres
   python scripts/alembic_cli.py revision --safe -m "deskripsi_perubahan_schema"
   ```

- Panduan operasional lengkap ada di [docs/MIGRATION_WORKFLOW.md](docs/MIGRATION_WORKFLOW.md).
- Template migration aman ada di [docs/SAFE_MIGRATION_TEMPLATE.md](docs/SAFE_MIGRATION_TEMPLATE.md).
- VS Code task dasar juga sudah tersedia di [.vscode/tasks.json](.vscode/tasks.json).
- Jika `-AdminUser` diberikan tanpa password, helper script akan mem-prompt password admin secara aman.

## Migrasi Schema yang Aman

- Default `DB_AUTO_MIGRATE=0` agar runtime app tidak melakukan `ALTER TABLE`.
- Untuk migrasi admin, set sementara `DB_ADMIN_PASSWORD` di environment lalu jalankan:

   ```powershell
   python scripts/migrate_user_password_schema.py
   ```

- Setelah migrasi selesai, hapus kembali `DB_ADMIN_PASSWORD` dari environment lokal bila tidak diperlukan.

## Troubleshooting PostgreSQL

- Jika muncul `password authentication failed`, berarti username/password pada `DATABASE_URL` tidak sesuai.
- Pastikan kredensial benar, lalu jalankan ulang aplikasi.
- Jika password mengandung karakter khusus (`@`, `:`, `/`), pakai `DB_*` agar tidak perlu URL encoding manual.
- Jika `.env` berubah, jalankan lagi `python src/main.py` atau `python -c "from src.database.models import test_connection; print(test_connection())"` untuk verifikasi.

## Troubleshooting Environment

- Jika import modul binary gagal, pastikan interpreter aktif mengarah ke workspace `.venv`, bukan Python global.
- Untuk verifikasi interpreter aktif di PowerShell, jalankan `python -c "import sys; print(sys.executable)"` dan pastikan hasilnya menunjuk ke `.venv\Scripts\python.exe`.
- Jika `.venv` terlihat korup parsial, perbaiki dengan reinstall dependency yang dipin:

   ```powershell
   python -m pip install --upgrade --force-reinstall --no-cache-dir -r requirements.txt
   ```

- Jika masalah tetap ada, hapus `.venv`, buat ulang environment, lalu install ulang:

   ```powershell
   Remove-Item -Recurse -Force .venv
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements-dev.txt
   ```

- Setelah pemulihan environment, jalankan `python -m pip check` lalu uji startup dengan `python src/main.py`.

## Troubleshooting VS Code AI Toolkit

- Jika muncul diagnostic `File 'azure-ai-foundry.commandPalette.deployWorkflow' not found` pada agent `AIAgentExpert.agent.md`, jalankan patch repo ini agar file extension lokal diperbaiki ulang setelah update extension:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\fix_ai_toolkit_agent_link.ps1
   ```

- Untuk verifikasi tanpa mengubah file, gunakan:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\fix_ai_toolkit_agent_link.ps1 -DryRun
   ```

## Struktur Folder

- src/ : Source code utama
- assets/ : File aset aplikasi

## Catatan

- Backup dan file sementara sudah dihapus.
- Untuk pengembangan, gunakan virtual environment workspace `.venv`.

## Kontak

Silakan hubungi pengembang untuk pertanyaan lebih lanjut.
