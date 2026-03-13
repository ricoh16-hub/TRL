# Migration Workflow

## Prinsip

- Runtime aplikasi memakai user `app_client`.
- Migrasi schema memakai user owner/admin schema.
- Jangan jalankan DDL dari runtime app kecuali benar-benar perlu.
- Simpan kredensial admin hanya sementara saat migrasi.

## Command Harian

Revision aktif saat ini: `20260313_02 (head)`.

### Cek revision aktif

```powershell
python scripts/alembic_cli.py current --admin-user postgres
```

> Script akan meminta password admin secara aman.

### Apply migration ke head

```powershell
python scripts/alembic_cli.py upgrade head --admin-user postgres
```

### Rollback satu step

```powershell
python scripts/alembic_cli.py downgrade -1 --admin-user postgres
```

### Buat revision baru

```powershell
python scripts/alembic_cli.py revision -m "add audit columns"
```

### Buat revision baru dengan checklist aman

```powershell
python scripts/alembic_cli.py revision --safe -m "add audit columns"
```

### Buat revision baru + autogenerate

```powershell
python scripts/alembic_cli.py revision --autogenerate --admin-user postgres -m "add audit columns"
```

## Checklist Sebelum Buat Migration

- Update model SQLAlchemy di `src/database/models.py`
- Pastikan perubahan schema memang perlu
- Tentukan apakah perubahan harus backward-compatible
- Siapkan default/backfill jika menambah kolom NOT NULL

## Checklist Sebelum Upgrade

- Backup database jika data penting
- Pastikan `DB_ADMIN_USER`/password tersedia
- Pastikan app tidak sedang menjalankan operasi schema sensitif
- Review isi file migration di `alembic/versions/`

## Checklist Sesudah Upgrade

- Jalankan:

```powershell
python -c "from src.database.models import test_connection; print(test_connection())"
```

- Jalankan app:

```powershell
python src/main.py
```

- Uji login / CRUD yang terdampak perubahan schema

## Catatan

- Untuk migration yang mengubah data, hindari autogenerate penuh tanpa review manual.
- Jika perlu akses admin sementara, lebih baik prompt password saat menjalankan script daripada menyimpan permanen di `.env`.

## Referensi Tambahan

- [docs/SAFE_MIGRATION_TEMPLATE.md](docs/SAFE_MIGRATION_TEMPLATE.md)
- [docs/examples/alembic_safe_revision_example.py](docs/examples/alembic_safe_revision_example.py)
- [alembic/versions/20260313_02_add_user_audit_timestamps.py](alembic/versions/20260313_02_add_user_audit_timestamps.py)
