import hashlib
import hmac
import os
from typing import Tuple


def generate_salt(length: int = 16) -> str:
    return os.urandom(length).hex()


def hash_password(password: str, salt: str, iterations: int = 100_000) -> str:
    password_bytes = password.encode("utf-8")
    salt_bytes = bytes.fromhex(salt)
    digest = hashlib.pbkdf2_hmac("sha256", password_bytes, salt_bytes, iterations)
    return digest.hex()


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    calculated_hash = hash_password(password, salt)
    return hmac.compare_digest(calculated_hash, stored_hash)


def create_password_hash(password: str) -> Tuple[str, str]:
    if not password:
        raise ValueError("Password tidak boleh kosong.")

    salt = generate_salt()
    password_hash = hash_password(password, salt)
    return salt, password_hash