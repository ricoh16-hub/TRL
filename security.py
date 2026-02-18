import os
import hashlib
import hmac
from typing import Tuple

def generate_salt(length: int = 16) -> str:
    """Generate salt acak dalam bentuk hex string."""
    return os.urandom(length).hex()

def hash_password(password: str, salt: str, iterations: int = 100_000) -> str:
    """Hash password login (bisa huruf/angka/simbol)."""
    pwd_bytes = password.encode("utf-8")
    salt_bytes = bytes.fromhex(salt)
    dk = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, iterations)
    return dk.hex()

def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    """Verifikasi password login."""
    calc_hash = hash_password(password, salt)
    return hmac.compare_digest(calc_hash, stored_hash)

def hash_pin(pin: str, salt: str, iterations: int = 50_000) -> str:
    """Hash PIN 6 digit."""
    pin_bytes = pin.encode("utf-8")
    salt_bytes = bytes.fromhex(salt)
    dk = hashlib.pbkdf2_hmac("sha256", pin_bytes, salt_bytes, iterations)
    return dk.hex()

def verify_pin(pin: str, salt: str, stored_hash: str) -> bool:
    """Verifikasi PIN 6 digit."""
    calc_hash = hash_pin(pin, salt)
    return hmac.compare_digest(calc_hash, stored_hash)

def create_password_hash(password: str) -> Tuple[str, str]:
    """Membuat salt + hash untuk password login."""
    salt = generate_salt()
    pwd_hash = hash_password(password, salt)
    return salt, pwd_hash

def create_pin_hash(pin: str) -> Tuple[str, str]:
    """Membuat salt + hash untuk PIN 6 digit."""
    if not (len(pin) == 6 and pin.isdigit()):
        raise ValueError("PIN harus 6 digit angka.")
    salt = generate_salt()
    pin_hash = hash_pin(pin, salt)
    return salt, pin_hash
