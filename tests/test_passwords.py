from src.auth.passwords import create_password_hash, generate_salt, verify_password


def test_generate_salt_returns_hex_string() -> None:
    salt = generate_salt()

    assert len(salt) == 32
    int(salt, 16)


def test_create_password_hash_round_trip() -> None:
    salt, password_hash = create_password_hash("rahasia-kuat")

    assert verify_password("rahasia-kuat", salt, password_hash)
    assert not verify_password("salah", salt, password_hash)


def test_create_password_hash_rejects_empty_password() -> None:
    try:
        create_password_hash("")
    except ValueError as error:
        assert "Password tidak boleh kosong" in str(error)
    else:
        raise AssertionError("Expected ValueError for empty password")