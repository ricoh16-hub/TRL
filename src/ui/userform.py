from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QListWidget, QLabel, QMessageBox
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.models import Session
from database.crud import create_user, read_users, update_user, delete_user


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
        self.username = QLineEdit(); self.username.setPlaceholderText('Username')
        self.password = QLineEdit(); self.password.setPlaceholderText('Password')
        self.role = QLineEdit(); self.role.setPlaceholderText('Role')
        self.layout.addWidget(self.username)
        self.layout.addWidget(self.password)
        self.layout.addWidget(self.role)
        self.add_btn = QPushButton('Tambah User')
        self.update_btn = QPushButton('Update User')
        self.delete_btn = QPushButton('Hapus User')
        self.layout.addWidget(self.add_btn)
        self.layout.addWidget(self.update_btn)
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
        self.delete_btn.clicked.connect(self.delete_user)

    def refresh_list(self):
        self.list_widget.clear()
        session = Session()
        users = read_users(session)
        for user in users:
            self.list_widget.addItem(f"{user.id}: {user.username} ({user.role})")
        session.close()

    def add_user(self):
        session = Session()
        create_user(session, self.username.text(), self.password.text(), self.role.text())
        session.close()
        self.refresh_list()

    def update_user(self):
        selected = self.list_widget.currentItem()
        if selected:
            user_id = int(selected.text().split(':')[0])
            session = Session()
            update_user(session, user_id, username=self.username.text(), password=self.password.text(), role=self.role.text())
            session.close()
            self.refresh_list()

    def delete_user(self):
        selected = self.list_widget.currentItem()
        if selected:
            user_id = int(selected.text().split(':')[0])
            session = Session()
            delete_user(session, user_id)
            session.close()
            self.refresh_list()