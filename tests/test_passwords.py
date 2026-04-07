from src.auth.passwords import create_password_hash, create_pin_hash, generate_salt, verify_password, verify_pin_code


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


def test_create_pin_hash_round_trip() -> None:
    salt, pin_hash = create_pin_hash("123456")

    assert verify_pin_code("123456", salt, pin_hash)
    assert not verify_pin_code("654321", salt, pin_hash)


def test_create_pin_hash_rejects_invalid_pin() -> None:
    for invalid_pin in ("", "12345", "1234567", "12a456"):
        try:
            create_pin_hash(invalid_pin)
        except ValueError as error:
            assert "PIN harus tepat 6 digit angka" in str(error)
        else:
            raise AssertionError("Expected ValueError for invalid PIN")


def test_verify_pin_code_with_valid_format_uses_hash_check() -> None:
    salt, pin_hash = create_pin_hash("123456")

    assert verify_pin_code("123456", salt, pin_hash) is True


def test_verify_pin_code_rejects_invalid_format() -> None:
    salt, pin_hash = create_pin_hash("123456")

    assert verify_pin_code("12345", salt, pin_hash) is False