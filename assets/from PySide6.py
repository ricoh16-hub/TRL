from PySide6.QtWidgets import QGraphicsDropShadowEffect

shadow = QGraphicsDropShadowEffect(self)
shadow.setBlurRadius(12)
shadow.setOffset(0, 4)
shadow.setColor(QColor(60, 80, 120, 120))  # Estetik, biru keabuan transparan
self.setGraphicsEffect(shadow)