import os
# Nonaktifkan log warning Qt (termasuk DPI awareness)
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
# Entry point aplikasi CRUD Database SQL Python
from PySide6.QtWidgets import QApplication
import sys
from ui.boot import show_boot
from ui.lock import show_lock
from ui.login import show_login

def main():
    """
    Entry point utama aplikasi CRUD Database SQL Python.
    Menampilkan boot screen, lock screen, dan login screen secara berurutan.
    """
    app_instance = QApplication.instance()
    app = app_instance if isinstance(app_instance, QApplication) else QApplication(sys.argv)
    try:
        show_boot()
        if show_lock():
            show_login(app)
    except KeyboardInterrupt:
        print("[INFO] Proses dihentikan manual. Keluar dengan elegan.")
if __name__ == "__main__":
    main()