#!/usr/bin/env python
"""
Audit script to verify data migration integrity.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.models import engine

def main():
    with engine.connect() as conn:
        print("=" * 80)
        print("1. USERS TABLE - Data Verification")
        print("=" * 80)
        result = conn.execute(text("""
            SELECT id, username, full_name, email, phone, status, created_at
            FROM users
            ORDER BY id
        """))
        rows = result.fetchall()
        print(f"Total users: {len(rows)}")
        for row in rows:
            print(f"  ID={row[0]}, username={row[1]}, full_name={row[2]}, email={row[3]}, phone={row[4]}, status={row[5]}")
        
        print("\n" + "=" * 80)
        print("2. ROLES TABLE - Data Verification")
        print("=" * 80)
        result = conn.execute(text("SELECT id, role_name, description FROM roles ORDER BY id"))
        rows = result.fetchall()
        print(f"Total roles: {len(rows)}")
        for row in rows:
            print(f"  ID={row[0]}, role_name={row[1]}, description={row[2]}")
        
        print("\n" + "=" * 80)
        print("3. USER_ROLES TABLE - Assignment Verification")
        print("=" * 80)
        result = conn.execute(text("""
            SELECT ur.id, ur.user_id, u.username, ur.role_id, r.role_name
            FROM user_roles ur
            JOIN users u ON ur.user_id = u.id
            JOIN roles r ON ur.role_id = r.id
            ORDER BY ur.user_id
        """))
        rows = result.fetchall()
        print(f"Total user-role assignments: {len(rows)}")
        for row in rows:
            print(f"  UserRole ID={row[0]}, User ID={row[1]} ({row[2]}), Role ID={row[3]} ({row[4]})")
        
        print("\n" + "=" * 80)
        print("4. USER_PASSWORDS TABLE - Verification")
        print("=" * 80)
        result = conn.execute(text("""
            SELECT up.id, up.user_id, u.username, up.password_hash IS NOT NULL as has_hash, up.password_salt IS NOT NULL as has_salt, up.updated_at
            FROM user_passwords up
            JOIN users u ON up.user_id = u.id
            ORDER BY up.user_id
        """))
        rows = result.fetchall()
        print(f"Total password records: {len(rows)}")
        for row in rows:
            print(f"  Password ID={row[0]}, User ID={row[1]} ({row[2]}), has_hash={row[3]}, has_salt={row[4]}")
        
        print("\n" + "=" * 80)
        print("5. USER_PINS TABLE - Verification")
        print("=" * 80)
        result = conn.execute(text("""
            SELECT up.id, up.user_id, u.username, up.pin_hash IS NOT NULL as has_hash, up.pin_salt IS NOT NULL as has_salt, up.updated_at
            FROM user_pins up
            JOIN users u ON up.user_id = u.id
            ORDER BY up.user_id
        """))
        rows = result.fetchall()
        print(f"Total PIN records: {len(rows)}")
        for row in rows:
            print(f"  PIN ID={row[0]}, User ID={row[1]} ({row[2]}), has_hash={row[3]}, has_salt={row[4]}")
        
        print("\n" + "=" * 80)
        print("6. DATA CONSISTENCY CHECKS")
        print("=" * 80)
        
        # Check for users without roles
        result = conn.execute(text("""
            SELECT u.id, u.username
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            WHERE ur.id IS NULL
        """))
        orphan_users = result.fetchall()
        print(f"Users without roles: {len(orphan_users)}")
        for row in orphan_users:
            print(f"  ID={row[0]}, username={row[1]}")
        
        # Check for users without passwords
        result = conn.execute(text("""
            SELECT u.id, u.username
            FROM users u
            LEFT JOIN user_passwords up ON u.id = up.user_id
            WHERE up.id IS NULL
        """))
        no_pwd_users = result.fetchall()
        print(f"Users without password records: {len(no_pwd_users)}")
        for row in no_pwd_users:
            print(f"  ID={row[0]}, username={row[1]}")
        
        # Check for users without pins
        result = conn.execute(text("""
            SELECT u.id, u.username
            FROM users u
            LEFT JOIN user_pins up ON u.id = up.user_id
            WHERE up.id IS NULL
        """))
        no_pin_users = result.fetchall()
        print(f"Users without PIN records: {len(no_pin_users)}")
        for row in no_pin_users:
            print(f"  ID={row[0]}, username={row[1]}")
        
        print("\n✅ Data migration verification complete!")

if __name__ == "__main__":
    main()
