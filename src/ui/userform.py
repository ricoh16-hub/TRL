from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, 
    QMessageBox, QTableWidget, QTableWidgetItem, QComboBox, QDialog,
    QFormLayout, QDialogButtonBox, QHeaderView
)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.models import Session
from database.crud import CANONICAL_ROLES, create_user, delete_user, normalize_role_name, read_users, update_user


class AddUserDialog(QDialog):
    """Dialog untuk menambahkan/edit user"""
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.setWindowTitle("Tambah User" if not user_data else "Edit User")
        self.setMinimumWidth(400)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Contoh: riko01")
        layout.addRow("Username:", self.username_input)
        
        # Nama
        self.nama_input = QLineEdit()
        self.nama_input.setPlaceholderText("Contoh: Riko Sinaga")
        layout.addRow("Nama:", self.nama_input)
        
        # Password (hanya untuk tambah baru)
        if not self.user_data:
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_input.setPlaceholderText("Password (required untuk user baru)")
            layout.addRow("Password:", self.password_input)
        
        # PIN
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setMaxLength(6)
        self.pin_input.setValidator(QIntValidator(0, 999999, self.pin_input))
        self.pin_input.setPlaceholderText("6 digit angka (opsional)")
        layout.addRow("PIN:", self.pin_input)
        
        # Role (ComboBox)
        self.role_combo = QComboBox()
        self.role_combo.addItems(list(CANONICAL_ROLES))
        self.role_combo.setCurrentText("Operator")
        layout.addRow("Role:", self.role_combo)
        
        # Status (ComboBox)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Aktif", "Nonaktif"])
        layout.addRow("Status:", self.status_combo)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Simpan")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Batal")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        
        self.setLayout(layout)
        
        # Isi data jika edit mode
        if self.user_data:
            self.username_input.setText(self.user_data.get("username", ""))
            self.username_input.setReadOnly(True)  # Username tidak bisa diubah
            self.nama_input.setText(self.user_data.get("nama", ""))
            self.pin_input.setText("")  # PIN tidak ditampilkan saat edit
            role_value = str(self.user_data.get("role", "Operator") or "Operator")
            try:
                role_value = normalize_role_name(role_value)
            except ValueError:
                role_value = "Operator"
            self.role_combo.setCurrentText(role_value)
            status_text = "Aktif" if self.user_data.get("status", "aktif").lower() == "aktif" else "Nonaktif"
            self.status_combo.setCurrentText(status_text)
    
    def get_data(self):
        """Mengembalikan data dari form"""
        data = {
            "username": self.username_input.text().strip(),
            "nama": self.nama_input.text().strip(),
            "role": self.role_combo.currentText(),
            "status": self.status_combo.currentText().lower(),
            "pin": self.pin_input.text().strip() if self.pin_input.text().strip() else "",
        }
        if not self.user_data:
            data["password"] = getattr(self, 'password_input', QLineEdit()).text()
        return data


class UserForm(QWidget):
    """
    Form manajemen user dengan table widget dan dialog modal
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Manajemen User')
        self.init_ui()
        self.refresh_table()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header dengan tombol tambah
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Manajemen User"))
        header_layout.addStretch()
        
        self.add_btn = QPushButton("+ Tambah User")
        self.add_btn.setMinimumHeight(36)
        self.add_btn.clicked.connect(self.open_add_user_dialog)
        header_layout.addWidget(self.add_btn)
        
        layout.addLayout(header_layout)
        
        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["No", "Username", "Nama", "Role", "Status", "Aksi"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        
        # Apply stylesheet
        sf_style = """
        * {
            font-family: 'SF Pro Display', 'San Francisco', 'Arial', sans-serif;
        }
        """
        self.setStyleSheet(sf_style)
    
    def refresh_table(self):
        """Refresh table dengan data user terbaru"""
        self.table.setRowCount(0)
        session = Session()
        try:
            users = read_users(session)
            for idx, user in enumerate(users, 1):
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # No
                self.table.setItem(row, 0, QTableWidgetItem(str(idx)))
                
                # Username
                self.table.setItem(row, 1, QTableWidgetItem(user.username))
                
                # Nama
                self.table.setItem(row, 2, QTableWidgetItem(user.nama or ""))
                
                # Role
                self.table.setItem(row, 3, QTableWidgetItem(user.role or ""))
                
                # Status
                status_text = "Aktif" if user.status and user.status.lower() == "aktif" else "Nonaktif"
                self.table.setItem(row, 4, QTableWidgetItem(status_text))
                
                # Aksi buttons
                aksi_widget = QWidget()
                aksi_layout = QHBoxLayout()
                aksi_layout.setContentsMargins(2, 2, 2, 2)
                
                edit_btn = QPushButton("Edit")
                edit_btn.clicked.connect(lambda checked, uid=user.id: self.open_edit_user_dialog(uid))
                
                delete_btn = QPushButton("Hapus")
                delete_btn.setStyleSheet("background-color: #dc3545;")
                delete_btn.clicked.connect(lambda checked, uid=user.id: self.delete_user(uid))
                
                aksi_layout.addWidget(edit_btn)
                aksi_layout.addWidget(delete_btn)
                aksi_widget.setLayout(aksi_layout)
                self.table.setCellWidget(row, 5, aksi_widget)
        finally:
            session.close()
    
    def open_add_user_dialog(self):
        """Buka dialog untuk menambah user baru"""
        dialog = AddUserDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.add_user(data)
    
    def open_edit_user_dialog(self, user_id):
        """Buka dialog untuk edit user"""
        session = Session()
        try:
            users = read_users(session)
            user = next((u for u in users if u.id == user_id), None)
            if not user:
                return
            
            user_data = {
                "id": user.id,
                "username": user.username,
                "nama": user.nama or "",
                "role": normalize_role_name(user.role or "Operator"),
                "status": user.status or "aktif",
            }
            
            dialog = AddUserDialog(self, user_data)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                self.update_user_data(user_id, data)
        finally:
            session.close()
    
    def add_user(self, data):
        """Tambah user baru ke database"""
        session = Session()
        try:
            if not data["username"]:
                QMessageBox.warning(self, "Validasi Gagal", "Username tidak boleh kosong.")
                return
            
            if not data.get("password"):
                QMessageBox.warning(self, "Validasi Gagal", "Password tidak boleh kosong untuk user baru.")
                return
            
            create_user(
                session,
                username=data["username"],
                nama=data.get("nama", ""),
                password=data["password"],
                role=data.get("role", "Operator"),
                pin=data.get("pin", ""),
                status=data.get("status", "aktif"),
            )
            self.refresh_table()
            QMessageBox.information(self, "Berhasil", f"User {data['username']} berhasil ditambahkan.")
        except ValueError as e:
            QMessageBox.warning(self, "Validasi Gagal", str(e))
            session.rollback()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {e}")
            session.rollback()
        finally:
            session.close()
    
    def update_user_data(self, user_id, data):
        """Update data user"""
        session = Session()
        try:
            update_user(
                session,
                user_id,
                nama=data.get("nama", ""),
                role=data.get("role", "Operator"),
                status=data.get("status", "aktif"),
            )
            self.refresh_table()
            QMessageBox.information(self, "Berhasil", "User berhasil diupdate.")
        except ValueError as e:
            QMessageBox.warning(self, "Validasi Gagal", str(e))
            session.rollback()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {e}")
            session.rollback()
        finally:
            session.close()
    
    def delete_user(self, user_id):
        """Hapus user dari database"""
        reply = QMessageBox.question(
            self,
            "Konfirmasi Hapus",
            "Apakah Anda yakin ingin menghapus user ini?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        session = Session()
        try:
            delete_user(session, user_id)
            self.refresh_table()
            QMessageBox.information(self, "Berhasil", "User berhasil dihapus.")
        except ValueError as e:
            QMessageBox.warning(self, "Validasi Gagal", str(e))
            session.rollback()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {e}")
            session.rollback()
        finally:
            session.close()