# FINAL RELEASE

## Cara Setup & Menjalankan Aplikasi

### 1. Persiapan Lingkungan
- Pastikan Python 3.9+ sudah terinstall.
- Install dependensi dengan perintah:
	```bash
	pip install -r requirements.txt
	```

### 2. Menjalankan Aplikasi
- Aktifkan virtual environment jika ada:
	```bash
	.venv\Scripts\activate
	```
- Jalankan aplikasi utama:
	```bash
	python src/main.py
	```

### 3. Struktur Folder Penting
- `src/ui/` : Semua file UI utama (form, widget)
- `src/auth/` : Modul autentikasi
- `src/database/` : Modul database dan model
- `assets/` : File gambar dan HTML

### 4. Catatan
- Untuk menjalankan demo webview: jalankan `app.py`.
- Untuk setup database: jalankan `init_db.py`.

---
Folder ini berisi semua file dan gambar yang sudah berjalan normal dan siap digunakan. Semua file test dan percobaan telah dipindahkan/hapus.
