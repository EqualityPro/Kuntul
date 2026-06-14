"""Test untuk utils/settings_store.py (penyimpanan Setup Wizard).

Memakai fixture `db` dari conftest.py (DB SQLite sementara dengan skema lengkap,
termasuk tabel `settings` yang dibuat init_db).
"""
import os


def test_init_db_creates_settings_table(db):
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None


def test_set_get_delete(db):
    from utils import settings_store as ss

    assert ss.get_setting("LOG_CHANNEL_ID") is None
    ss.set_setting("LOG_CHANNEL_ID", 123456)
    assert ss.get_setting("LOG_CHANNEL_ID") == "123456"  # disimpan sebagai string

    assert ss.all_settings().get("LOG_CHANNEL_ID") == "123456"

    assert ss.delete_setting("LOG_CHANNEL_ID") is True
    assert ss.get_setting("LOG_CHANNEL_ID") is None
    # Hapus yang tidak ada -> False, tidak error.
    assert ss.delete_setting("LOG_CHANNEL_ID") is False


def test_set_setting_overwrites(db):
    from utils import settings_store as ss
    ss.set_setting("STORE_NAME", "Toko A")
    ss.set_setting("STORE_NAME", "Toko B")
    assert ss.get_setting("STORE_NAME") == "Toko B"


def test_set_setting_does_not_touch_os_environ(db):
    """set_setting sengaja TIDAK mengubah os.environ (sumber kebenaran = DB).

    Penerapan ke environ dilakukan terpisah lewat apply_to_environ()/config.refresh().
    """
    from utils import settings_store as ss
    key = "SETTINGS_STORE_TEST_KEY_XYZ"
    os.environ.pop(key, None)
    ss.set_setting(key, "hello")
    assert key not in os.environ


def test_apply_to_environ_overrides_target(db):
    from utils import settings_store as ss
    ss.set_setting("LOG_CHANNEL_ID", "999")
    ss.set_setting("STORE_NAME", "Toko Overlay")

    target = {}
    n = ss.apply_to_environ(target)
    assert n == 2
    assert target["LOG_CHANNEL_ID"] == "999"
    assert target["STORE_NAME"] == "Toko Overlay"


def test_apply_to_environ_skips_empty_values(db):
    """Nilai kosong dianggap 'belum diatur' -> tidak menimpa (biar .env menang)."""
    from utils import settings_store as ss
    ss.set_setting("DANA_NUMBER", "08123")
    ss.set_setting("BCA_NUMBER", "   ")  # kosong/spasi

    target = {}
    ss.apply_to_environ(target)
    assert target.get("DANA_NUMBER") == "08123"
    assert "BCA_NUMBER" not in target


def test_apply_to_environ_no_db_file_safe(db, monkeypatch, tmp_path):
    """Bila file DB belum ada, apply_to_environ aman & tidak membuat file baru."""
    from utils import settings_store as ss
    import utils.db as realdb

    ghost = str(tmp_path / "does_not_exist.db")
    monkeypatch.setattr(realdb, "DB_FILE", ghost)
    target = {}
    assert ss.apply_to_environ(target) == 0
    assert target == {}
    assert not os.path.exists(ghost)


def test_apply_to_environ_uses_os_environ_by_default(db, monkeypatch):
    from utils import settings_store as ss
    key = "SETTINGS_STORE_DEFAULT_ENV_KEY"
    monkeypatch.delenv(key, raising=False)
    ss.set_setting(key, "from-db")
    ss.apply_to_environ()  # tanpa argumen -> os.environ
    assert os.environ.get(key) == "from-db"



def test_config_refresh_applies_wizard_setting(db):
    """utils.config.refresh() harus memuat ulang nilai dari settings store."""
    import importlib
    import sys
    from utils import settings_store as ss

    # Test lain (test_ticket_ui) mengganti sys.modules['utils.config'] dengan
    # stub SimpleNamespace. Muat ulang modul ASLI agar test ini mandiri, lalu
    # pulihkan state semula supaya tidak mempengaruhi test berikutnya.
    _prev = sys.modules.pop("utils.config", None)
    try:
        cfg = importlib.import_module("utils.config")

        ss.set_setting("MAX_TICKETS_PER_SERVICE", "9")
        cfg.refresh()
        assert cfg.MAX_TICKETS_PER_SERVICE == 9

        ss.set_setting("STORE_NAME", "Toko Refresh")
        cfg.refresh()
        assert cfg.STORE_NAME == "Toko Refresh"

        # Reset -> kembali ke default config.
        ss.delete_setting("MAX_TICKETS_PER_SERVICE")
        cfg.refresh()
        assert cfg.MAX_TICKETS_PER_SERVICE == 5
    finally:
        if _prev is not None:
            sys.modules["utils.config"] = _prev
        else:
            sys.modules.pop("utils.config", None)
