#!/usr/bin/env python
"""
Script untuk seed/menambahkan user contoh ke database
Sesuai dengan contoh di assets/MANAGEMENT_USERS.JPG
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import Session
from src.database.crud import create_user

# Data user contoh dari MANAGEMENT_USERS.JPG
SAMPLE_USERS = [
    {
        "username": "riko01",
        "nama": "Riko Sinaga",
        "password": "Password@123",
        "pin": "111111",
        "role": "Admin",
        "status": "aktif",
    },
    {
        "username": "agus02",
        "nama": "Agus Setiawan",
        "password": "Password@123",
        "pin": "222222",
        "role": "Manager",
        "status": "aktif",
    },
    {
        "username": "budi02",
        "nama": "Budi Santoso",
        "password": "Password@123",
        "pin": "333333",
        "role": "Staff",
        "status": "aktif",
    },
    {
        "username": "sinta04",
        "nama": "Sinta Dewi",
        "password": "Password@123",
        "pin": "444444",
        "role": "Staff",
        "status": "aktif",
    },
    {
        "username": "joko05",
        "nama": "Joko Saputra",
        "password": "Password@123",
        "pin": "555555",
        "role": "Staff",
        "status": "aktif",
    },
    {
        "username": "andi06",
        "nama": "Andi Pratama",
        "password": "Password@123",
        "pin": "666666",
        "role": "Staff",
        "status": "aktif",
    },
    {
        "username": "dewi07",
        "nama": "Dewi Lestari",
        "password": "Password@123",
        "pin": "777777",
        "role": "Staff",
        "status": "aktif",
    },
    {
        "username": "nano08",
        "nama": "Nanang Harmoko",
        "password": "Password@123",
        "pin": "888888",
        "role": "Staff",
        "status": "aktif",
    },
]


def main():
    from src.database.models import User
    from sqlalchemy.exc import IntegrityError
    
    session = Session()
    try:
        added_count = 0
        skipped_count = 0
        
        for user_data in SAMPLE_USERS:
            try:
                # Cek apakah user sudah ada
                existing_user = session.query(User).filter_by(username=user_data["username"]).first()
                if existing_user:
                    print(f"⊘ User sudah ada: {user_data['username']} ({existing_user.nama}) - Role: {existing_user.role}")
                    skipped_count += 1
                    continue
                
                user = create_user(
                    session=session,
                    username=user_data["username"],
                    nama=user_data["nama"],
                    password=user_data["password"],
                    pin=user_data["pin"],
                    role=user_data["role"],
                    status=user_data["status"],
                )
                print(f"✓ User ditambahkan: {user.username} ({user.nama}) - Role: {user.role}")
                added_count += 1
            except (ValueError, IntegrityError) as e:
                print(f"✗ Error menambahkan {user_data['username']}: {e}")
                session.rollback()

        print(f"\n✓ Ringkasan:")
        print(f"  - Ditambahkan: {added_count}")
        print(f"  - Sudah ada: {skipped_count}")
        print(f"  - Total: {len(SAMPLE_USERS)}")
    except Exception as e:
        print(f"✗ Error fatal: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
