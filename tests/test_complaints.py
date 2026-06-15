"""Test untuk utils/complaints.py (sistem komplain/refund)."""


def test_init_creates_table(db):
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='complaints'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None


def test_create_and_get(db):
    from utils import complaints as cp
    cid = cp.create_complaint(123, "rizky", "Permintaan refund", "barang gagal", "ORD-1")
    assert isinstance(cid, int) and cid > 0
    c = cp.get_complaint(cid)
    assert c["user_id"] == 123
    assert c["category"] == "Permintaan refund"
    assert c["related_order"] == "ORD-1"
    assert c["status"] == "baru"


def test_list_and_filter(db):
    from utils import complaints as cp
    a = cp.create_complaint(1, "a", "Lainnya", "x")
    cp.create_complaint(2, "b", "Lainnya", "y")
    cp.set_status(a, "selesai")
    assert len(cp.list_complaints()) >= 2
    baru = cp.list_complaints(status="baru")
    assert all(c["status"] == "baru" for c in baru)
    selesai = cp.list_complaints(status="selesai")
    assert any(c["id"] == a for c in selesai)


def test_set_status_validation(db):
    from utils import complaints as cp
    cid = cp.create_complaint(9, "z", "Lainnya", "halo")
    assert cp.set_status(cid, "diproses") is True
    assert cp.get_complaint(cid)["status"] == "diproses"
    assert cp.set_status(cid, "status-ngawur") is False  # status invalid ditolak
    assert cp.get_complaint(cid)["status"] == "diproses"


def test_admin_note(db):
    from utils import complaints as cp
    cid = cp.create_complaint(5, "y", "Lainnya", "test")
    assert cp.set_admin_note(cid, "sudah dihubungi") is True
    assert cp.get_complaint(cid)["admin_note"] == "sudah dihubungi"


def test_stats(db):
    from utils import complaints as cp
    cp.create_complaint(1, "a", "Permintaan refund", "x")
    cp.create_complaint(2, "b", "Permintaan refund", "y")
    c = cp.create_complaint(3, "c", "Lainnya", "z")
    cp.set_status(c, "selesai")
    s = cp.stats()
    assert s["total"] == 3
    assert s["by_status"]["baru"] == 2
    assert s["by_status"]["selesai"] == 1
    assert s["open"] == 2
    assert s["by_category"][0][0] == "Permintaan refund"  # terbanyak
    assert s["by_category"][0][1] == 2
