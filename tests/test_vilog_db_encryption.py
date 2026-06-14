"""Test enkripsi at-rest pada utils/vilog_db.py."""


def _sample_ticket(channel_id=555):
    return {
        "channel_id": channel_id,
        "user_id": 42,
        "username_roblox": "buyer@example.com",
        "email": "buyer@example.com",
        "password": "SuperSecret!123",
        "backup_codes": "aaa-111\nbbb-222\nccc-333",
        "premium": True,
        "boost": {"nama": "Vilog", "robux": 1000},
        "metode": "vilog",
        "nominal": 50000,
        "admin_id": None,
        "opened_at": "2026-01-01T00:00:00+00:00",
        "warned": False,
        "ticket_number": 7,
    }


def test_credentials_encrypted_in_db(db, monkeypatch):
    """Setelah save, kolom sensitif di DB harus ciphertext (sb1:), bukan plaintext."""
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci-test")
    from utils import vilog_db

    t = _sample_ticket()
    vilog_db.save_vilog_ticket(t)

    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT username_roblox, password, email, backup_codes "
            "FROM vilog_tickets WHERE channel_id=?", (t["channel_id"],)
        ).fetchone()
    finally:
        conn.close()

    for col in ("username_roblox", "password", "email", "backup_codes"):
        assert row[col].startswith("sb1:"), f"{col} tidak terenkripsi"
    # Plaintext asli tidak boleh muncul di DB.
    assert "SuperSecret!123" not in row["password"]
    assert "buyer@example.com" not in row["email"]
    assert "aaa-111" not in row["backup_codes"]


def test_round_trip_load_decrypts(db, monkeypatch):
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci-test")
    from utils import vilog_db

    t = _sample_ticket(channel_id=556)
    vilog_db.save_vilog_ticket(t)
    loaded = vilog_db.load_vilog_tickets()[556]

    assert loaded["email"] == "buyer@example.com"
    assert loaded["password"] == "SuperSecret!123"
    assert loaded["backup_codes"] == "aaa-111\nbbb-222\nccc-333"
    assert loaded["premium"] is True
    assert loaded["ticket_number"] == 7


def test_backward_compat_plaintext_rows(db, monkeypatch):
    """Baris lama yang masih plaintext tetap terbaca apa adanya."""
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci-test")
    from utils import vilog_db

    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO vilog_tickets (channel_id, user_id, username_roblox, "
            "password, email, backup_codes, premium, boost_nama, boost_robux, "
            "metode, nominal, admin_id, opened_at, warned, ticket_number) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (777, 1, "old@mail.com", "oldpass", "old@mail.com",
             "z1\nz2\nz3", 0, "Vilog", 500, "vilog", 25000, None,
             "2026-01-01T00:00:00+00:00", 0, 3),
        )
        conn.commit()
    finally:
        conn.close()

    loaded = vilog_db.load_vilog_tickets()[777]
    assert loaded["password"] == "oldpass"
    assert loaded["email"] == "old@mail.com"
    assert loaded["backup_codes"] == "z1\nz2\nz3"


def test_delete_removes_credentials(db, monkeypatch):
    monkeypatch.setenv("VILOG_SECRET_KEY", "kunci-test")
    from utils import vilog_db

    t = _sample_ticket(channel_id=558)
    vilog_db.save_vilog_ticket(t)
    vilog_db.delete_vilog_ticket(558)

    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM vilog_tickets WHERE channel_id=?", (558,)
        ).fetchone()
    finally:
        conn.close()
    assert row is None
    assert 558 not in vilog_db.load_vilog_tickets()
