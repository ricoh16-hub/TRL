"""Script untuk mengecek lebar setiap digit pada label jam lock.py"""
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontMetrics
import sys

app = QApplication(sys.argv)

# Konfigurasi untuk hour_label
font_hour = QFont('SF Pro Display')
font_hour.setPointSizeF(160.0)
font_hour.setWeight(QFont.Weight.ExtraLight)
font_hour.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -4.0)

# Konfigurasi untuk minute_label
font_minute = QFont('SF Pro Display')
font_minute.setPointSizeF(160.0)
font_minute.setWeight(QFont.Weight.Light)
font_minute.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -2.0)

metrics_hour = QFontMetrics(font_hour)
metrics_minute = QFontMetrics(font_minute)

print("=" * 60)
print("LEBAR SETIAP DIGIT PADA LABEL JAM FORM LOCK.PY")
print("=" * 60)
print()

print("HOUR LABEL (Font Weight: ExtraLight, Letter Spacing: -4.0):")
print("-" * 60)
for digit in '0123456789':
    width = metrics_hour.horizontalAdvance(digit)
    print(f"Digit '{digit}': {width:.2f} px")

print()
print("MINUTE LABEL (Font Weight: Light, Letter Spacing: -2.0):")
print("-" * 60)
for digit in '0123456789':
    width = metrics_minute.horizontalAdvance(digit)
    print(f"Digit '{digit}': {width:.2f} px")

print()
print("CONTOH LEBAR DUA DIGIT:")
print("-" * 60)
print(f"Hour '00': {metrics_hour.horizontalAdvance('00'):.2f} px")
print(f"Hour '12': {metrics_hour.horizontalAdvance('12'):.2f} px")
print(f"Hour '23': {metrics_hour.horizontalAdvance('23'):.2f} px")
print(f"Minute '00': {metrics_minute.horizontalAdvance('00'):.2f} px")
print(f"Minute '30': {metrics_minute.horizontalAdvance('30'):.2f} px")
print(f"Minute '59': {metrics_minute.horizontalAdvance('59'):.2f} px")

print()
print("=" * 60)

app.quit()
