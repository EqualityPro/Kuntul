"""Penyimpanan setting via Setup Wizard (`/setup` atau `!setup`).

Tujuan: menurunkan friksi self-host ("config sprawl"). Alih-alih mengisi
puluhan ID channel/role di .env secara manual, admin menjalankan setup wizard
dan memilih channel/role lewat dropdown native Discord. Nilainya disimpan di
tabel `settings` (SQLite) lalu DITIMPA ke os.environ oleh utils.config saat
startup — sehingga SELURUH kode lama yang membaca config (`os.getenv(...)` di
utils/config.py) TIDAK perlu diubah.

Prioritas nilai: setting wizard (tabel ini) > .env > default di utils.config.

Modul ini sengaja murni-SQLite (tanpa Discord) supaya gampang di-unit-test dan
aman diimpor sangat awal saat startup.
"""
import datetime
import os


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def init_settings_table():
    """Buat tabel settings bila belum ada (idempoten)."""
    from utils.db import get_conn
    conn = get_conn()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                key        TEXT PRIMARY KEY,
                value      TEXT,
                updated_at TEXT
            )"""
        )
        conn.commit()
    finally:
        conn.close()


def all_settings() -> dict:
    """Semua setting tersimpan sebagai {key: value}. Aman bila tabel belum ada."""
    from utils.db import get_conn
    conn = get_conn()
    try:
        try:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        except Exception:
            return {}
        return {r["key"]: r["value"] for r in rows}
    finally:
        conn.close()


def get_setting(key, default=None):
    """Ambil satu nilai setting (string) atau `default` bila tidak ada."""
    from utils.db import get_conn
    conn = get_conn()
    try:
        try:
            row = conn.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
        except Exception:
            return default
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key, value):
    """Simpan/timpa satu setting. Nilai disimpan sebagai string.

    Catatan: modul ini sengaja TIDAK menyentuh os.environ. Pemanggil (wizard)
    memanggil utils.config.refresh() setelah menyimpan, yang akan menerapkan
    ulang seluruh setting ke environ dari satu sumber kebenaran (tabel ini).
    """
    init_settings_table()
    from utils.db import get_conn
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?,?,?)",
            (key, "" if value is None else str(value), _now()),
        )
        conn.commit()
    finally:
        conn.close()


def delete_setting(key) -> bool:
    """Hapus setting (mis. reset ke default .env). True bila ada yang terhapus."""
    from utils.db import get_conn
    conn = get_conn()
    try:
        try:
            cur = conn.execute("DELETE FROM settings WHERE key=?", (key,))
            conn.commit()
            return cur.rowcount > 0
        except Exception:
            return False
    finally:
        conn.close()


def apply_to_environ(environ=None) -> int:
    """Timpa nilai setting tersimpan ke os.environ. Return jumlah yang ditimpa.

    Dipanggil oleh utils.config (saat import & saat refresh) supaya perubahan
    via wizard langsung berlaku tanpa mengedit .env. Aman dipanggil walau DB /
    tabel belum ada (tidak meng-raise, tidak membuat file DB baru).
    """
    if environ is None:
        environ = os.environ
    # Jangan buat file DB baru hanya untuk membaca setting (mis. saat config
    # diimpor sebelum init_db pada deploy yang benar-benar baru).
    try:
        from utils.db import DB_FILE
        if not os.path.exists(DB_FILE):
            return 0
    except Exception:
        return 0

    try:
        data = all_settings()
    except Exception:
        return 0

    n = 0
    for k, v in data.items():
        if v is None or str(v).strip() == "":
            # String kosong = "belum diatur" -> biarkan .env / default menang.
            continue
        environ[k] = str(v)
        n += 1
    return n
