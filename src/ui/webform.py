from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView

class WebForm(QWidget):
    """
    Widget untuk menampilkan halaman web menggunakan QWebEngineView.
    URL default: https://www.example.com
    """
    def __init__(self, url='https://www.example.com'):
        super().__init__()
        self.setWindowTitle('Hybrid Web Form')
        layout = QVBoxLayout()
        self.webview = QWebEngineView()
        self.webview.setUrl(url)
        layout.addWidget(self.webview)
        self.setLayout(layout)
        # Terapkan stylesheet global agar konsisten
        sf_style = """
        * {
            font-family: 'SF Pro Display', 'San Francisco', 'Arial', sans-serif;
        }
        """
        self.setStyleSheet(sf_style)