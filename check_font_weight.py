"""Script untuk mengecek nilai font weight pada label jam lock.py"""
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
import sys

app = QApplication(sys.argv)

print("=" * 60)
print("FONT WEIGHT PADA LABEL JAM FORM LOCK.PY")
print("=" * 60)
print()

# Font weight yang digunakan saat ini
hour_weight = QFont.Weight.ExtraLight
minute_weight = QFont.Weight.Light

print("KONFIGURASI SAAT INI:")
print("-" * 60)
print(f"Hour Label Weight: QFont.Weight.ExtraLight = {hour_weight.value}")
print(f"Minute Label Weight: QFont.Weight.Light = {minute_weight.value}")
print()

print("REFERENSI NILAI QFont.Weight:")
print("-" * 60)
print(f"Thin       = {QFont.Weight.Thin.value}")
print(f"ExtraLight = {QFont.Weight.ExtraLight.value}")
print(f"Light      = {QFont.Weight.Light.value}")
print(f"Normal     = {QFont.Weight.Normal.value}")
print(f"Medium     = {QFont.Weight.Medium.value}")
print(f"DemiBold   = {QFont.Weight.DemiBold.value}")
print(f"Bold       = {QFont.Weight.Bold.value}")
print(f"ExtraBold  = {QFont.Weight.ExtraBold.value}")
print(f"Black      = {QFont.Weight.Black.value}")
print()

print("CATATAN:")
print("-" * 60)
print("Nilai weight berkisar dari 100 (Thin) hingga 900 (Black)")
print("Semakin tinggi nilai, semakin tebal fontnya")
print()
print("Untuk jam yang lebih tipis, coba gunakan:")
print("  - Hour: QFont.Weight.Thin (100)")
print("  - Minute: QFont.Weight.ExtraLight atau Thin")
print()
print("=" * 60)

app.quit()
