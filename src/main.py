import os
# Nonaktifkan log warning Qt (termasuk DPI awareness)
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
# Entry point aplikasi CRUD Database SQL Python
from PySide6.QtWidgets import QApplication
import sys
from ui.boot import show_boot
from ui.lock import show_lock
from ui.login import show_login
from database.models import init_db

def main():
    """
    Entry point utama aplikasi CRUD Database SQL Python.
    Menampilkan boot screen, lock screen, dan login screen secara berurutan.
    """
    app_instance = QApplication.instance()
    app = app_instance if isinstance(app_instance, QApplication) else QApplication(sys.argv)
    try:
        init_db()
        show_boot()
        if show_lock():
            show_login(app)
    except RuntimeError as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("[INFO] Proses dihentikan manual. Keluar dengan elegan.")
if __name__ == "__main__":
    main()