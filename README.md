# README

## Deskripsi

Aplikasi ini adalah aplikasi Python yang telah dioptimalkan dan dibersihkan dari file tidak penting.

## Cara Menjalankan

1. Pastikan Python 3.10+ sudah terinstall.

2. Install dependensi:

   ```bash
   pip install -r requirements.txt
   ```

3. Siapkan PostgreSQL dan buat database, misalnya `app_db`.

4. Set koneksi PostgreSQL.

   Best practice: pakai user database aplikasi khusus, bukan `postgres`.

   Disarankan pakai variable terpisah (lebih aman):

   ```powershell
   $env:DB_USER = "app_client"
   $env:DB_PASSWORD = "PASSWORD_APP_DB_ANDA"
   $env:DB_HOST = "localhost"
   $env:DB_PORT = "5432"
   $env:DB_NAME = "app_db"
   $env:DB_CONNECT_TIMEOUT = "10"
   $env:DB_APP_NAME = "python-apps-12R"
   ```

   Alternatif (single URL):

   ```powershell
   $env:DATABASE_URL = "postgresql+psycopg2://app_client:PASSWORD_APP_DB_ANDA@localhost:5432/app_db"
   ```

   Atau gunakan file `.env`:

   - Copy `.env.example` menjadi `.env`
   - Isi `DB_PASSWORD` dengan password app DB user yang benar

5. Jalankan aplikasi:

   ```bash
   python src/main.py
   ```

## Koneksi Database (Multi User)

- Aplikasi sekarang menggunakan PostgreSQL melalui SQLAlchemy.
- Connection pooling aktif (pool size 10, max overflow 20, pre-ping aktif) agar aman untuk akses concurrent/multi-user.
- Tabel akan diinisialisasi otomatis saat startup aplikasi.
- File `.env` dibaca relatif dari root project, jadi tidak tergantung current working directory.
- Gunakan role DB non-superuser dengan privilege minimum untuk runtime aplikasi.
- Runtime aplikasi tidak disarankan menjalankan DDL otomatis. Gunakan migrasi admin terpisah untuk perubahan schema.

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
- Helper script PowerShell untuk Windows tersedia di folder [scripts](scripts).
- [scripts/alembic-current.ps1](scripts/alembic-current.ps1)
- [scripts/alembic-upgrade.ps1](scripts/alembic-upgrade.ps1)
- [scripts/alembic-downgrade.ps1](scripts/alembic-downgrade.ps1)
- [scripts/alembic-revision.ps1](scripts/alembic-revision.ps1)
- [scripts/alembic-revision-safe.ps1](scripts/alembic-revision-safe.ps1)

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

## Struktur Folder

- src/ : Source code utama
- assets/ : File aset aplikasi

## Catatan

- Backup dan file sementara sudah dihapus.
- Untuk pengembangan, gunakan virtual environment baru.

## Kontak

Silakan hubungi pengembang untuk pertanyaan lebih lanjut.
