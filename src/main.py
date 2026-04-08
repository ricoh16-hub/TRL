import os
# Nonaktifkan log warning Qt (termasuk DPI awareness)
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
from pathlib import Path
from PySide6.QtWidgets import QApplication
import sys
from ui.login import show_login
from ui.credentials_login import show_credentials_login
from ui.dashboard import show_dashboard
from database.models import init_db


def _best_effort_sync_app_privileges() -> None:
    """Best-effort grant privilege app user jika kredensial admin tersedia."""
    try:
        from dotenv import dotenv_values
        import psycopg2
    except Exception:
        return

    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"
    raw_env = dotenv_values(env_path)
    env = {str(key): str(value) for key, value in raw_env.items() if value is not None}

    host = os.getenv("DB_HOST") or env.get("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT") or env.get("DB_PORT", "5432"))
    db_name = os.getenv("DB_NAME") or env.get("DB_NAME", "GBR")
    app_user = os.getenv("DB_USER") or env.get("DB_USER", "app_client")
    admin_user = os.getenv("DB_ADMIN_USER") or env.get("DB_ADMIN_USER", "")
    admin_password = os.getenv("DB_ADMIN_PASSWORD") or env.get("DB_ADMIN_PASSWORD", "")

    if not admin_user or not admin_password:
        return

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=db_name,
            user=admin_user,
            password=admin_password,
        )
        conn.autocommit = True
        try:
            with conn.cursor() as cursor:
                cursor.execute(f'GRANT CONNECT ON DATABASE "{db_name}" TO "{app_user}"')
                cursor.execute(f'GRANT USAGE ON SCHEMA public TO "{app_user}"')
                cursor.execute(
                    f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{app_user}"'
                )
                cursor.execute(
                    f'GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO "{app_user}"'
                )
            print("[INFO] Privilege app user synchronized")
        finally:
            conn.close()
    except Exception as error:
        print(f"[WARN] Gagal sinkronisasi privilege app user: {error}")

def main():
    """
    Entry point utama aplikasi.
    Alur: PIN -> username/password -> dashboard.
    """
    app_instance = QApplication.instance()
    app = app_instance if isinstance(app_instance, QApplication) else QApplication(sys.argv)
    try:
        _best_effort_sync_app_privileges()
        init_db()
        pin_user = show_login(app)
        if pin_user is None:
            return

        authenticated_user = show_credentials_login(app, pin_user)
        if authenticated_user is None:
            return

        dashboard = show_dashboard(app, authenticated_user)
        dashboard.raise_()
        dashboard.activateWindow()
        app.exec()
    except RuntimeError as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("[INFO] Proses dihentikan manual. Keluar dengan elegan.")
if __name__ == "__main__":
    main()