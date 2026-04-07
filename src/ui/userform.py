from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QListWidget, QLabel, QMessageBox, QListWidgetItem
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.models import Session
from database.crud import create_user, read_users, update_user, delete_user, set_user_pin


class UserForm(QWidget):
    """
    Form manajemen user CRUD (Create, Read, Update, Delete) berbasis PySide6.
    Menampilkan daftar user, serta input untuk username, password, dan role.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Manajemen User')
        self.layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.layout.addWidget(QLabel('Daftar User'))
        self.layout.addWidget(self.list_widget)
        self.username = QLineEdit()
        self.username.setPlaceholderText('Username')
        self.password = QLineEdit()
        self.password.setPlaceholderText('Password')
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin = QLineEdit()
        self.pin.setPlaceholderText('PIN (6 digit angka)')
        self.pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin.setMaxLength(6)
        self.pin.setValidator(QIntValidator(0, 999999, self.pin))
        self.role = QLineEdit()
        self.role.setPlaceholderText('Role')
        self.layout.addWidget(self.username)
        self.layout.addWidget(self.password)
        self.layout.addWidget(self.pin)
        self.layout.addWidget(self.role)
        self.add_btn = QPushButton('Tambah User')
        self.update_btn = QPushButton('Update User')
        self.pin_btn = QPushButton('Daftarkan / Ganti PIN User')
        self.delete_btn = QPushButton('Hapus User')
        self.layout.addWidget(self.add_btn)
        self.layout.addWidget(self.update_btn)
        self.layout.addWidget(self.pin_btn)
        self.layout.addWidget(self.delete_btn)
        self.setLayout(self.layout)
        # Terapkan stylesheet global agar konsisten
        sf_style = """
        * {
            font-family: 'SF Pro Display', 'San Francisco', 'Arial', sans-serif;
        }
        """
        self.setStyleSheet(sf_style)
        self.refresh_list()
        self.add_btn.clicked.connect(self.add_user)
        self.update_btn.clicked.connect(self.update_user)
        self.pin_btn.clicked.connect(self.register_or_change_pin)
        self.delete_btn.clicked.connect(self.delete_user)
        self.list_widget.itemSelectionChanged.connect(self.sync_form_from_selected_user)

    def refresh_list(self):
        self.list_widget.clear()
        session = Session()
        users = read_users(session)
        for user in users:
            pin_status = 'PIN aktif' if user.pin_hash and user.pin_salt else 'PIN belum diatur'
            item = QListWidgetItem(f"{user.id}: {user.username} ({user.role}) - {pin_status}")
            item.setData(Qt.ItemDataRole.UserRole, user.id)
            self.list_widget.addItem(item)
        session.close()

    def _get_selected_user_id(self) -> int | None:
        selected = self.list_widget.currentItem()
        if selected is None:
            return None

        user_id = selected.data(Qt.ItemDataRole.UserRole)
        if isinstance(user_id, int):
            return user_id
        return None

    def sync_form_from_selected_user(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            return

        session = Session()
        try:
            users = read_users(session)
            user = next((item for item in users if item.id == user_id), None)
            if user is None:
                return

            self.username.setText(user.username)
            self.role.setText(user.role or 'user')
            self.password.clear()
            self.pin.clear()
        finally:
            session.close()

    def add_user(self):
        session = Session()
        try:
            create_user(
                session,
                self.username.text(),
                self.password.text(),
                self.role.text(),
                pin=self.pin.text(),
            )
            self.username.clear()
            self.password.clear()
            self.pin.clear()
            self.role.clear()
            self.refresh_list()
            QMessageBox.information(self, 'Berhasil', 'User baru berhasil ditambahkan.')
        except ValueError as error:
            QMessageBox.warning(self, 'Validasi Gagal', str(error))
            session.rollback()
        finally:
            session.close()

    def update_user(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            QMessageBox.warning(self, 'Validasi Gagal', 'Pilih user dulu untuk diupdate.')
            return

        session = Session()
        try:
            update_user(session, user_id, username=self.username.text(), password=self.password.text(), role=self.role.text())
            self.password.clear()
            self.refresh_list()
            QMessageBox.information(self, 'Berhasil', 'Data user berhasil diupdate.')
        except ValueError as error:
            QMessageBox.warning(self, 'Validasi Gagal', str(error))
            session.rollback()
        finally:
            session.close()

    def register_or_change_pin(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            QMessageBox.warning(self, 'Validasi Gagal', 'Pilih user dulu untuk daftar/ganti PIN.')
            return

        session = Session()
        try:
            set_user_pin(session, user_id, self.pin.text())
            self.pin.clear()
            self.refresh_list()
            QMessageBox.information(self, 'Berhasil', 'PIN user berhasil didaftarkan/diganti.')
        except ValueError as error:
            QMessageBox.warning(self, 'Validasi Gagal', str(error))
            session.rollback()
        finally:
            session.close()

    def delete_user(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            QMessageBox.warning(self, 'Validasi Gagal', 'Pilih user dulu untuk dihapus.')
            return

        session = Session()
        try:
            delete_user(session, user_id)
            self.refresh_list()
            QMessageBox.information(self, 'Berhasil', 'User berhasil dihapus.')
        except ValueError as error:
            QMessageBox.warning(self, 'Validasi Gagal', str(error))
            session.rollback()
        finally:
            session.close()