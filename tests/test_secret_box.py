"""Test untuk utils/secret_box.py (enkripsi at-rest kredensial Vilog)."""


def test_round_trip_with_key(monkeypatch):
    from utils import secret_box
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci-rahasia-uji-yang-panjang")
    assert secret_box.enabled() is True

    plain = "Password123!@#"
    token = secret_box.encrypt(plain)
    assert token.startswith("sb1:")
    assert plain not in token  # ciphertext tidak memuat plaintext
    assert secret_box.decrypt(token) == plain


def test_unicode_and_multiline(monkeypatch):
    from utils import secret_box
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci")
    plain = "kode1\nkode2\nkode3\náé😀"
    assert secret_box.decrypt(secret_box.encrypt(plain)) == plain


def test_empty_values(monkeypatch):
    from utils import secret_box
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci")
    assert secret_box.encrypt("") == ""
    assert secret_box.encrypt(None) == ""
    assert secret_box.decrypt("") == ""
    assert secret_box.decrypt(None) == ""


def test_plaintext_passthrough_on_decrypt(monkeypatch):
    """Nilai tanpa prefix sb1: (baris lama plaintext) dikembalikan apa adanya."""
    from utils import secret_box
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci")
    assert secret_box.decrypt("password-lama-plaintext") == "password-lama-plaintext"
    assert secret_box.is_encrypted("password-lama-plaintext") is False


def test_idempotent_encrypt(monkeypatch):
    from utils import secret_box
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci")
    once = secret_box.encrypt("rahasia")
    twice = secret_box.encrypt(once)  # sudah terenkripsi -> tidak dobel
    assert once == twice
    assert secret_box.decrypt(twice) == "rahasia"


def test_no_key_falls_back_to_plaintext(monkeypatch):
    """Tanpa VILOG_SECRET_KEY & TOKEN, encrypt mengembalikan plaintext."""
    from utils import secret_box
    monkeypatch.delenv("VILOG_SECRET_KEY", raising=False)
    monkeypatch.delenv("TOKEN", raising=False)
    assert secret_box.enabled() is False
    assert secret_box.encrypt("apa adanya") == "apa adanya"


def test_token_used_when_no_secret_key(monkeypatch):
    from utils import secret_box
    monkeypatch.delenv("VILOG_SECRET_KEY", raising=False)
    monkeypatch.setenv("TOKEN", "token-bot-rahasia")
    assert secret_box.enabled() is True
    assert secret_box.decrypt(secret_box.encrypt("x")) == "x"


def test_tamper_detection(monkeypatch):
    """Ciphertext yang diubah -> MAC gagal -> kembalikan string kosong."""
    from utils import secret_box
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci")
    token = secret_box.encrypt("data penting")
    # Ubah satu karakter base64 di tengah.
    body = token[len("sb1:"):]
    flipped = ("A" if body[10] != "A" else "B")
    tampered = "sb1:" + body[:10] + flipped + body[11:]
    assert secret_box.decrypt(tampered) == ""


def test_wrong_key_cannot_decrypt(monkeypatch):
    from utils import secret_box
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci-A")
    token = secret_box.encrypt("rahasia")
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci-B")
    assert secret_box.decrypt(token) == ""
