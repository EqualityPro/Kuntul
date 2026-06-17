"""Tema/kustomisasi Kartu Umum "Order Selesai" (logika murni, tanpa PIL/discord).

Kembaran dari utils/rating_theme.py & utils/achievement_theme.py, tapi untuk
KARTU UMUM yang dikirim saat order selesai dan buyer TIDAK membuka badge baru.
Kartu ini dilampirkan ke pesan log transaksi (render_general_card di
cogs/profile.py, dipanggil cogs/reviews.update_success_log).

Tujuan: tiap pembeli tetap menerima sebuah kartu ucapan terima kasih walau
mereka belum mencapai milestone badge. Bila buyer membuka badge baru, kartu
achievement-lah yang dipakai (kartu umum dilewati) — sesuai pilihan toko.

Kartu menyediakan BANYAK elemen yang bisa diatur admin lewat panel. Elemen inti
(avatar, judul, nama, pesan, produk) tampil secara default; elemen tambahan
(harga, qty, layanan, tanggal, admin, no. order, rating, tier, level, total
order/belanja, ulasan, member sejak, badge top spender, subjudul, CTA, footer,
logo) DEFAULTNYA DISEMBUNYIKAN supaya kartu tidak penuh — admin tinggal
menampilkan yang dibutuhkan.

Jenis elemen:
  - "avatar": foto profil buyer (avatar_bytes).
  - "icon"  : gambar logo/ikon toko (di-upload admin: data/general_icon.<ext>).
  - "stars" : bintang rating digambar sebagai bentuk (bukan teks).
  - "text"  : teks. STATIS bila punya atribut "text" (judul/pesan/subjudul/CTA/
              footer); DINAMIS bila tidak (nilainya berasal dari transaksi/profil
              lewat dict `values`, dilewati bila tidak ada).

Flag `enabled` (default False) menentukan apakah kartu umum dikirim. Bila
nonaktif, perilaku lama dipertahankan (pesan log diedit tanpa kartu).

Tema disimpan sebagai JSON di tabel `bot_state` (key `general_card_theme`),
sehingga admin panel (Flask) & bot (discord) berbagi sumber yang sama.

Kanvas kartu berukuran GENERAL_W x GENERAL_H. Semua koordinat relatif ke kanvas.
"""

import json

from utils import card_theme_base as _base

THEME_KEY = "general_card_theme"

# Ukuran kanvas kartu umum (banner lebar; sama dengan kartu testimoni).
GENERAL_W = 1024
GENERAL_H = 450

# Kanvas acuan koordinat default. Disamakan dgn kanvas saat ini -> tanpa skala.
_LEGACY_CANVAS = (GENERAL_W, GENERAL_H)

# Batas panjang teks statis (title/message/subtitle/cta/footer).
MAX_TEXT_LEN = 120

# Warna bingkai (ring) avatar default (hijau "selesai").
RING_DEFAULT = "#3DD68C"

# Teks statis default (bisa diedit admin).
DEFAULT_TITLE = "ORDER SELESAI"
DEFAULT_MESSAGE = "Terima kasih sudah order! Ditunggu pesanan berikutnya ya."
DEFAULT_SUBTITLE = "Pesanan kamu sudah selesai diproses"
DEFAULT_CTA = "Order lagi yuk, banyak promo menarik!"
DEFAULT_FOOTER = "Terima kasih telah berbelanja"

# Elemen yang bisa dikustomisasi + default-nya. Koordinat/ukuran ditulis relatif
# ke `_LEGACY_CANVAS`, lalu diskalakan ke kanvas saat ini di _build_default().
#
# Elemen INTI default show=True; elemen TAMBAHAN default show=False (admin
# tinggal menampilkan yang dipakai). Elemen teks DINAMIS tidak punya atribut
# "text" (nilainya dari `values`); elemen teks STATIS punya "text".
_LEGACY_DEFAULT = {
    "enabled": False,              # False = tidak kirim kartu umum (perilaku lama)
    "panel_opacity": 150,          # 0-255, panel gelap di atas background
    "font_file": None,             # nama file font di data/ (None = font default)
    "embed": {"enabled": False, "color": "#3DD68C"},  # bungkus kartu dalam embed
    "elements": {
        # ── Inti (tampil default) ──────────────────────────────────────────
        "avatar":  {"type": "avatar", "x": 60,  "y": 100, "size": 170, "show": True,  "ring_color": RING_DEFAULT},
        "title":   {"type": "text",   "x": 288, "y": 34,  "size": 30, "color": "#3DD68C", "bold": True,  "show": True,  "text": DEFAULT_TITLE},
        "name":    {"type": "text",   "x": 288, "y": 100, "size": 40, "color": "#FFFFFF", "bold": True,  "show": True},
        "message": {"type": "text",   "x": 288, "y": 196, "size": 24, "color": "#E2E4EC", "bold": False, "show": True,  "text": DEFAULT_MESSAGE, "wrap": True},
        "product": {"type": "text",   "x": 288, "y": 268, "size": 26, "color": "#9DE9C2", "bold": True,  "show": True},
        # ── Dekoratif ──────────────────────────────────────────────────────
        "icon":    {"type": "icon",   "x": 844, "y": 40,  "size": 150, "show": False},
        "stars":   {"type": "stars",  "x": 288, "y": 150, "size": 28, "color": "#FFD24D", "show": False},
        # ── Statis tambahan ────────────────────────────────────────────────
        "subtitle":{"type": "text",   "x": 288, "y": 74,  "size": 20, "color": "#CFE9DD", "bold": False, "show": False, "text": DEFAULT_SUBTITLE},
        "cta":     {"type": "text",   "x": 288, "y": 406, "size": 20, "color": "#9DE9C2", "bold": True,  "show": False, "text": DEFAULT_CTA},
        "footer":  {"type": "text",   "x": 724, "y": 418, "size": 16, "color": "#9AA7A2", "bold": False, "show": False, "text": DEFAULT_FOOTER},
        # ── Dinamis dari transaksi ─────────────────────────────────────────
        "rating":  {"type": "text",   "x": 540, "y": 150, "size": 24, "color": "#FFD24D", "bold": True,  "show": False},
        "layanan": {"type": "text",   "x": 288, "y": 304, "size": 20, "color": "#BFE8D6", "bold": False, "show": False},
        "harga":   {"type": "text",   "x": 288, "y": 338, "size": 22, "color": "#FFFFFF", "bold": True,  "show": False},
        "qty":     {"type": "text",   "x": 470, "y": 338, "size": 22, "color": "#FFFFFF", "bold": False, "show": False},
        "tanggal": {"type": "text",   "x": 288, "y": 374, "size": 18, "color": "#C9D2CE", "bold": False, "show": False},
        "seller":  {"type": "text",   "x": 470, "y": 374, "size": 18, "color": "#C9D2CE", "bold": False, "show": False},
        "order_no":{"type": "text",   "x": 660, "y": 374, "size": 18, "color": "#C9D2CE", "bold": False, "show": False},
        # ── Dinamis dari profil member ─────────────────────────────────────
        "tier":         {"type": "text", "x": 724, "y": 100, "size": 24, "color": "#F0C85A", "bold": True,  "show": False},
        "level":        {"type": "text", "x": 724, "y": 136, "size": 20, "color": "#E7E0CC", "bold": False, "show": False},
        "total_orders": {"type": "text", "x": 724, "y": 170, "size": 20, "color": "#FFFFFF", "bold": False, "show": False},
        "total_spent":  {"type": "text", "x": 724, "y": 204, "size": 18, "color": "#CFE9DD", "bold": False, "show": False},
        "spent_month":  {"type": "text", "x": 724, "y": 234, "size": 18, "color": "#CFE9DD", "bold": False, "show": False},
        "total_reviews":{"type": "text", "x": 724, "y": 264, "size": 18, "color": "#CFE9DD", "bold": False, "show": False},
        "member_since": {"type": "text", "x": 724, "y": 294, "size": 18, "color": "#C9D2CE", "bold": False, "show": False},
        "topspender":   {"type": "text", "x": 724, "y": 328, "size": 20, "color": "#F0C85A", "bold": True,  "show": False},
    },
}


def _build_default() -> dict:
    """DEFAULT_THEME pada kanvas saat ini (koordinat legacy diskalakan + penanda)."""
    theme = json.loads(json.dumps(_LEGACY_DEFAULT))
    theme["canvas"] = [GENERAL_W, GENERAL_H]
    lw, lh = _LEGACY_CANVAS
    if (GENERAL_W, GENERAL_H) != (lw, lh):
        _base.rescale_elements(theme["elements"], GENERAL_W / lw, GENERAL_H / lh)
    return theme


DEFAULT_THEME = _build_default()

# Urutan & label ramah untuk ditampilkan di editor (dikelompokkan).
ELEMENT_LABELS = [
    ("avatar", "Foto Profil"),
    ("icon", "Logo/Ikon Toko"),
    ("title", "Judul"),
    ("subtitle", "Subjudul"),
    ("name", "Nama Pembeli"),
    ("stars", "Bintang (gambar)"),
    ("rating", "Rating (teks)"),
    ("message", "Pesan Ucapan"),
    ("product", "Produk/Item"),
    ("layanan", "Kategori Layanan"),
    ("harga", "Harga"),
    ("qty", "Jumlah"),
    ("tanggal", "Tanggal Order"),
    ("seller", "Admin/CS"),
    ("order_no", "No. Order"),
    ("tier", "Tier Member"),
    ("level", "Level"),
    ("total_orders", "Total Order"),
    ("total_spent", "Total Belanja"),
    ("spent_month", "Belanja Bulan Ini"),
    ("total_reviews", "Jumlah Ulasan"),
    ("member_since", "Member Sejak"),
    ("topspender", "Badge Top Spender"),
    ("cta", "Ajakan (CTA)"),
    ("footer", "Footer/Nama Toko"),
]

# Urutan render & iterasi (key saja).
ELEMENT_ORDER = [k for k, _ in ELEMENT_LABELS]

# Key elemen teks DINAMIS (nilai dari `values`, bukan teks statis). Dipakai
# renderer & untuk dokumentasi/validasi. Elemen statis = punya atribut "text".
DYNAMIC_TEXT_KEYS = [
    "name", "rating", "product", "layanan", "harga", "qty", "tanggal",
    "seller", "order_no", "tier", "level", "total_orders", "total_spent",
    "spent_month", "total_reviews", "member_since", "topspender",
]


# Helper umum dipusatkan di utils/card_theme_base.py. Alias lokal dipertahankan
# untuk kompatibilitas (kode lain & test yang mengaksesnya langsung).
_clampi = _base.clampi
_valid_hex = _base.valid_hex
hex_to_rgb = _base.hex_to_rgb


def _scale_factors(raw, cw, ch):
    """Faktor skala (sx, sy) dari kanvas tema tersimpan ke (cw, ch) saat ini.

    Pakai penanda `canvas`; tema lama tanpa penanda dianggap `_LEGACY_CANVAS`.
    """
    rc = raw.get("canvas") if isinstance(raw, dict) else None
    if isinstance(rc, (list, tuple)) and len(rc) == 2:
        try:
            ocw, och = int(rc[0]), int(rc[1])
        except (TypeError, ValueError):
            ocw, och = _LEGACY_CANVAS
    else:
        ocw, och = _LEGACY_CANVAS
    if ocw <= 0 or och <= 0 or (ocw, och) == (cw, ch):
        return 1.0, 1.0
    return cw / ocw, ch / och


def _smul(v, s):
    """Kalikan nilai numerik dengan faktor `s` (bulatkan). Non-numerik dibiarkan."""
    if s == 1.0:
        return v
    try:
        return int(round(float(v) * s))
    except (TypeError, ValueError):
        return v


def default_theme() -> dict:
    """Salinan dalam dari DEFAULT_THEME (aman dimodifikasi pemanggil)."""
    return json.loads(json.dumps(DEFAULT_THEME))


def merge_theme(raw) -> dict:
    """Gabungkan tema tersimpan dengan default + validasi nilai.

    Toleran: input None/rusak/sebagian -> dilengkapi default. Elemen/atribut
    asing diabaikan. Struktur (type/text/wrap) selalu dari default; hanya nilai
    yang bisa diedit admin (posisi, ukuran, warna, bold, show, teks statis,
    ring) yang diambil dari `raw`. Selalu mengembalikan tema lengkap & valid.
    """
    theme = default_theme()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = None
    if not isinstance(raw, dict):
        return theme

    # Skalakan koordinat/ukuran bila tema dibuat untuk kanvas berukuran lain.
    sx, sy = _scale_factors(raw, GENERAL_W, GENERAL_H)

    theme["enabled"] = bool(raw.get("enabled", theme["enabled"]))
    theme["panel_opacity"] = _clampi(raw.get("panel_opacity"), 0, 255,
                                     theme["panel_opacity"])
    ff = raw.get("font_file")
    theme["font_file"] = ff if (isinstance(ff, str) and ff.strip()) else None

    raw_embed = raw.get("embed") if isinstance(raw.get("embed"), dict) else {}
    theme["embed"]["enabled"] = bool(raw_embed.get("enabled", theme["embed"]["enabled"]))
    theme["embed"]["color"] = _valid_hex(raw_embed.get("color", theme["embed"]["color"]),
                                         theme["embed"]["color"])

    raw_elems = raw.get("elements") if isinstance(raw.get("elements"), dict) else {}
    for key, base in theme["elements"].items():
        incoming = raw_elems.get(key)
        if not isinstance(incoming, dict):
            continue
        if "x" in incoming:
            base["x"] = _clampi(_smul(incoming["x"], sx), 0, GENERAL_W, base["x"])
        if "y" in incoming:
            base["y"] = _clampi(_smul(incoming["y"], sy), 0, GENERAL_H, base["y"])
        base["show"] = bool(incoming.get("show", base["show"]))
        typ = base["type"]
        if typ == "text":
            if "size" in incoming:
                base["size"] = _clampi(_smul(incoming["size"], sy), 8, 120, base["size"])
            base["color"] = _valid_hex(incoming.get("color", base["color"]), base["color"])
            base["bold"] = bool(incoming.get("bold", base["bold"]))
        elif typ == "stars":
            if "size" in incoming:
                base["size"] = _clampi(_smul(incoming["size"], sy), 8, 120, base["size"])
            base["color"] = _valid_hex(incoming.get("color", base["color"]), base["color"])
        elif typ == "avatar":
            if "size" in incoming:
                base["size"] = _clampi(_smul(incoming["size"], sy), 32, 320, base["size"])
            base["ring_color"] = _valid_hex(incoming.get("ring_color", base["ring_color"]),
                                            base["ring_color"])
        elif typ == "icon":
            if "size" in incoming:
                base["size"] = _clampi(_smul(incoming["size"], sy), 32, 360, base["size"])
        if "text" in base:
            t = incoming.get("text", base["text"])
            if isinstance(t, str) and t.strip():
                base["text"] = t.strip()[:MAX_TEXT_LEN]
    return theme


def load_theme() -> dict:
    """Baca tema dari bot_state (atau default bila belum ada)."""
    return merge_theme(_base.read_state(THEME_KEY))


def save_theme(raw) -> dict:
    """Validasi + simpan tema ke bot_state. Mengembalikan tema final."""
    theme = merge_theme(raw)
    _base.write_state(THEME_KEY, theme)
    return theme
