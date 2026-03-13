# Safe Migration Template

## Prinsip

Gunakan pola **expand -> migrate data -> contract**.

- **Expand**: tambah kolom/tabel/index baru yang kompatibel dengan kode lama.
- **Migrate data**: backfill data lama ke format baru.
- **Contract**: hapus kolom lama / ketatkan constraint setelah aplikasi stabil.

## Pola Aman yang Direkomendasikan

### 1. Menambah kolom baru

Aman:

- tambah kolom nullable
- deploy aplikasi
- backfill data
- ubah ke NOT NULL pada migration berikutnya

Hindari:

- langsung tambah kolom NOT NULL tanpa default/backfill

### 2. Rename kolom

Aman:

- tambah kolom baru
- copy data dari kolom lama
- aplikasi baca dua kolom sementara
- pindahkan seluruh pemakaian ke kolom baru
- hapus kolom lama di migration terpisah

### 3. Hapus kolom / tabel

Aman:

- pastikan tidak dipakai aplikasi
- pastikan backup tersedia
- lakukan di migration terpisah

### 4. Perubahan data besar

Aman:

- lakukan batch update
- log jumlah row terdampak
- pastikan downgrade jelas atau tandai irreversible secara eksplisit

## Skeleton Upgrade/Downgrade

Lihat contoh lengkap di [docs/examples/alembic_safe_revision_example.py](docs/examples/alembic_safe_revision_example.py).

## Checklist Review Migration

- Apakah `upgrade()` backward-compatible?
- Apakah `downgrade()` realistis dan aman?
- Apakah ada operasi yang butuh lock lama?
- Apakah index dibuat pada tahap yang tepat?
- Apakah data backfill sudah dipikirkan?
- Apakah migration sudah diuji di database salinan / lokal?
