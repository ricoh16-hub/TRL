# Referensi Desain Form Utama Lock.py

Dokumen ini adalah catatan standar untuk desain "seperti form utama lock.py".
Jika nanti disebut memakai desain form utama lock.py, acuannya adalah metode,
palet, layer, border, glow, dan perilaku state charging / tidak charging di
`src/ui/lock.py`, terutama `AuthenticLockScreen.paintEvent`.

## Prinsip Utama

- `lock.py` adalah acuan utama. Jangan mengubah visual `lock.py` untuk mengejar
  form lain; form lain yang harus mengikuti metode ini.
- Tampilan utama bukan warna flat. Form harus dibangun dengan beberapa layer:
  base gradient, diagonal accent, radial focus glow, top highlight, lower
  accent, edge shading, bottom depth, inner border, dan outer border gradient.
- Semua elemen utama harus membaca state charging yang sama, lalu mengubah
  warna secara harmonis. Charging memakai aksen aqua/electric blue. Tidak
  charging memakai putih/off-white dengan depth abu gelap.
- Efek premium berasal dari alpha yang halus, bukan warna terang berlebihan.
  Glow harus lembut dan terkontrol.
- Radius form utama mengikuti karakter lock.py: rounded rectangle premium
  dengan corner radius sekitar `22px`, border tipis, dan inset `1px`.

## Form Utama: Tidak Charging

Palet tidak charging dari `AuthenticLockScreen.paintEvent`:

- Background top: `QColor(26, 32, 41)`
- Background middle: `QColor(41, 49, 60)`
- Background bottom: `QColor(31, 39, 50)`
- Accent top: `QColor(255, 255, 255, 18)`
- Accent bottom: `QColor(205, 216, 228, 10)`
- Border main: `QColor(255, 255, 255, 45)`
- Inner highlight: `QColor(255, 255, 255, 27)`
- Lower shadow: `QColor(0, 0, 0, 42)`
- Focus glow: `QColor(255, 255, 255, 20)`
- Inner border: `QColor(255, 255, 255, 24)`
- Lower accent: `QColor(205, 216, 228, 9)`
- Edge shadow: `QColor(0, 0, 0, 22)`
- Border top: `QColor(255, 255, 255, 44)`
- Border bottom: `QColor(205, 216, 228, 20)`

Karakter visual:

- Kesan utama: graphite glass, putih lembut, dingin, tidak ramai.
- Elemen icon/text dominan putih atau off-white.
- Glow putih hanya sebagai depth, bukan highlight besar.
- Border terlihat tipis dan rapi, bukan outline tebal.

## Form Utama: Charging

Palet charging dari `AuthenticLockScreen.paintEvent`:

- Background top: `QColor(18, 30, 43)`
- Background middle: `QColor(31, 47, 64)`
- Background bottom: `QColor(20, 36, 55)`
- Accent top: `QColor(103, 224, 255, 34)`
- Accent bottom: `QColor(55, 138, 238, 18)`
- Border main: `QColor(103, 224, 255, 64)`
- Inner highlight: `QColor(232, 250, 255, 34)`
- Lower shadow: `QColor(4, 16, 30, 44)`
- Focus glow: `QColor(103, 224, 255, 30)`
- Inner border: `QColor(232, 250, 255, 28)`
- Lower accent: `QColor(55, 138, 238, 16)`
- Edge shadow: `QColor(2, 12, 24, 26)`
- Border top: `QColor(232, 250, 255, 54)`
- Border bottom: `QColor(55, 138, 238, 26)`

Karakter visual:

- Kesan utama: blue glass premium, tetap gelap, bukan biru terang penuh.
- Aksen charging muncul di border, glow, icon, battery, lock, date/time, dan
  control terkait.
- Biru utama yang sering dipakai elemen: `#50B4FF`, dengan gradient aqua:
  `#4ED9FF` ke `#5AA7FF`.
- Charging harus terasa aktif dan hidup, tetapi tetap satu keluarga dengan
  state tidak charging.

## Urutan Layer Form Utama

Gunakan urutan paint seperti `AuthenticLockScreen.paintEvent`:

1. Clear transparent background dengan `CompositionMode_Source`.
2. Buat `rect` dengan inset `1px` dan radius sekitar `22px`.
3. Draw base vertical `QLinearGradient`:
   top -> middle pada `0.48` -> bottom.
4. Clip ke rounded path.
5. Draw diagonal accent `QLinearGradient`:
   kiri atas -> kanan bawah, alpha rendah.
6. Draw radial focus glow:
   center x, posisi y sekitar `top + 42px`, radius sekitar `178px`.
7. Draw top highlight:
   vertical gradient dari top ke `top + 18px`.
8. Draw lower accent:
   radial gradient di dekat `bottom - 4px`, radius sekitar `118px`.
9. Draw edge shading:
   horizontal gradient, gelap di kiri/kanan, transparan di tengah.
10. Draw bottom depth:
    vertical gradient dari `bottom - 30px` ke bottom.
11. Matikan clipping.
12. Draw inner border:
    inset sekitar `1.05px`, pen `0.65px`, cosmetic.
13. Draw outer border:
    vertical border gradient, pen `1px`, cosmetic.

## Aturan Elemen di Dalam Form

- Semua elemen premium harus sinkron dengan charging state.
- Battery:
  - Charging: fill gradient aqua `#4ED9FF` ke `#5AA7FF`, ada simbol petir.
  - Tidak charging: fill putih ke abu muda.
- Wi-Fi:
  - Jika connected dan charging: biru `#50B4FF`.
  - Jika tidak connected atau tidak charging: putih.
- Lock icon:
  - Charging: gradient aqua/electric blue.
  - Tidak charging: putih/off-white dengan subtle depth.
- Clock/date:
  - Charging mengikuti palet biru lock.py.
  - Tidak charging mengikuti putih/off-white.
- Chevron/keycap/gear:
  - Hover glow charging: biru lembut.
  - Hover glow tidak charging: putih lembut.

## Checklist Saat Menerapkan ke Form Lain

- Jangan memakai warna flat tunggal untuk background.
- Jangan memakai border tebal atau terlalu kontras.
- Jangan membuat charging menjadi neon penuh; cukup aksen biru premium.
- Jangan membuat tidak charging terlalu hitam polos; harus ada middle tone,
  top highlight, lower shadow, dan edge shading.
- Pastikan bentuk utama, radius, inset, depth bawah, dan border gradient sama
  pendekatannya dengan `lock.py`.
- Pastikan state charging dan tidak charging diuji visualnya.
- Jika ada form lain seperti credentials login, security pin, atau splash,
  form itu harus mengikuti `lock.py`, bukan sebaliknya.

## Ringkasan Cepat

Jika diminta "design seperti form utama lock.py":

- Pakai rounded form radius sekitar `22px`.
- Pakai layered glass background sesuai urutan di atas.
- Tidak charging: graphite glass + putih/off-white.
- Charging: dark blue glass + aqua/electric blue accents.
- Border: inner border halus + outer border gradient.
- Glow: radial, alpha rendah, terpusat dekat bagian atas.
- Semua elemen mengikuti charging state secara konsisten.
- `lock.py` tidak diubah; form lain yang disesuaikan.
