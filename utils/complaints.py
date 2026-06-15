"""Sistem komplain/refund terstruktur.

Customer mengajukan komplain lewat /komplain (cogs/complaints.py). Admin
mengelola status & catatan lewat Admin Panel (halaman /complaints) atau tombol
di channel admin. Data disimpan di tabel `complaints`.

Modul ini murni-SQLite (tanpa Discord) supaya gampang di-unit-test.
"""
import datetime

from utils.db import get_conn

# Status alur komplain (urut siklus hidup).
STATUSES = ("baru", "diproses", "selesai", "ditolak")

# Kategori/alasan komplain yang bisa dipilih customer.
CATEGORIES = (
    "Pesanan belum diproses",
    "Barang/akun tidak sesuai",
    "Akun bermasalah / garansi",
    "Permintaan refund",
    "Lainnya",
)


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def init_complaints():
    """Buat tabel complaints bila belum ada (idempoten)."""
    conn = get_conn()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS complaints (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER,
                username      TEXT,
                category      TEXT,
                detail        TEXT,
                related_order TEXT DEFAULT '',
                status        TEXT DEFAULT 'baru',
                admin_note    TEXT DEFAULT '',
                created_at    TEXT,
                updated_at    TEXT
            )"""
        )
        conn.commit()
    finally:
        conn.close()



def create_complaint(user_id, username, category, detail, related_order=""):
    """Simpan komplain baru. Return id komplain."""
    init_complaints()
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO complaints (user_id, username, category, detail, "
            "related_order, status, created_at, updated_at) "
            "VALUES (?,?,?,?,?, 'baru', ?, ?)",
            (user_id, username, category, detail, related_order or "", _now(), _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_complaints(status=None, limit=300):
    """Daftar komplain (opsional filter status), terbaru dulu."""
    conn = get_conn()
    try:
        if status and status in STATUSES:
            rows = conn.execute(
                "SELECT * FROM complaints WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM complaints ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_complaint(cid):
    conn = get_conn()
    try:
        r = conn.execute("SELECT * FROM complaints WHERE id=?", (cid,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def set_status(cid, status):
    """Ubah status komplain. Return True bila berhasil & status valid."""
    if status not in STATUSES:
        return False
    conn = get_conn()
    try:
        cur = conn.execute(
            "UPDATE complaints SET status=?, updated_at=? WHERE id=?",
            (status, _now(), cid),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def set_admin_note(cid, note):
    conn = get_conn()
    try:
        cur = conn.execute(
            "UPDATE complaints SET admin_note=?, updated_at=? WHERE id=?",
            (note or "", _now(), cid),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def stats():
    """Rekap: total, jumlah per status, jumlah per kategori, jumlah 'terbuka'."""
    conn = get_conn()
    try:
        by_status = {s: 0 for s in STATUSES}
        for r in conn.execute(
            "SELECT status, COUNT(*) AS n FROM complaints GROUP BY status"
        ).fetchall():
            if r["status"] in by_status:
                by_status[r["status"]] = r["n"]
        by_category = [
            (r["category"], r["n"])
            for r in conn.execute(
                "SELECT category, COUNT(*) AS n FROM complaints "
                "GROUP BY category ORDER BY n DESC"
            ).fetchall()
        ]
        total = sum(by_status.values())
        return {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "open": by_status["baru"] + by_status["diproses"],
        }
    finally:
        conn.close()
