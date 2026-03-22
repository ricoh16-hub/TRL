# Centralized PostgreSQL Checklist

Dokumen ini dipakai untuk operasional aplikasi multi-user dengan 1 database PostgreSQL terpusat.

## 1) Konfigurasi aplikasi

- Set `DB_CENTRAL_MODE=1` di `.env`.
- Set `DB_HOST` ke IP/hostname server PostgreSQL terpusat (bukan localhost).
- Set `DB_AUTO_MIGRATE=0` pada semua client runtime.
- Set `DB_SSLMODE=require` (atau `verify-ca` / `verify-full` bila sertifikat sudah disiapkan).
- Gunakan `DB_USER` khusus aplikasi (misalnya `app_client`), bukan akun `postgres`.

## 2) User dan hak akses

- Buat 2 akun terpisah:
  - `app_client`: untuk runtime aplikasi (CRUD harian, tanpa DDL).
  - akun admin migrasi: owner schema untuk menjalankan Alembic.
- Rotasi password user aplikasi secara berkala.
- Simpan kredensial di secret manager atau environment machine lokal.

## 3) Jaringan dan keamanan

- Batasi akses port PostgreSQL hanya dari subnet aplikasi atau VPN.
- Nonaktifkan akses publik jika tidak diperlukan.
- Aktifkan TLS (`DB_SSLMODE`) untuk koneksi client-server.
- Pastikan firewall server database aktif.

## 4) Migrasi schema

- Jalankan migrasi hanya dari mesin admin:
  - `python scripts/alembic_cli.py current --admin-user postgres`
  - `python scripts/alembic_cli.py upgrade head --admin-user postgres`
- Verifikasi revision aktif ada di `head` setelah deploy.
- Jangan menjalankan migrasi schema dari client runtime.

## 5) Backup dan recovery

- Jadwalkan backup harian otomatis (minimal 1x per hari).
- Simpan retensi backup minimal 7-14 hari.
- Uji restore backup minimal 1x per bulan.
- Dokumentasikan RPO/RTO yang disepakati tim.

## 6) Validasi sebelum go-live

- Uji login serentak dari minimal 2-3 client.
- Uji skenario putus koneksi database (aplikasi harus gagal dengan pesan jelas).
- Uji failover operasional: restore backup terakhir ke environment uji.
- Catat host, port, user runtime, dan revision Alembic aktif pada handoff release.
