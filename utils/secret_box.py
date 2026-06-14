"""Enkripsi 'at rest' untuk data sensitif (kredensial Vilog).

Kenapa ada modul ini:
  Tiket Vilog menyimpan email, password, & kode backup akun Roblox milik
  customer. Sebelumnya disimpan PLAINTEXT di tabel `vilog_tickets`. File DB
  (`midman.db`) juga di-upload utuh ke channel backup Discord (utils/backup.py),
  sehingga password ikut bocor ke channel itu. Modul ini mengenkripsi field
  sensitif sebelum masuk DB, dan mendekripsi saat dibaca admin di runtime.

Desain (sengaja tanpa dependensi pihak ketiga supaya cepat dipasang & lolos CI):
  - Kunci diturunkan dari env `VILOG_SECRET_KEY` bila diset, kalau tidak dari
    `TOKEN` (selalu ada di .env). Kunci TIDAK pernah disimpan di DB — kalau
    disimpan di DB, enkripsi jadi sia-sia karena DB itu yang kita lindungi.
  - Skema: encrypt-then-MAC. Keystream = SHA-256 dalam mode counter; tag =
    HMAC-SHA256 (diverifikasi konstan-waktu). Format token: "sb1:<base64>".

Catatan jujur: ini BUKAN kriptografi kelas-militer. Ia memakai primitif standar
(SHA-256/HMAC) untuk melindungi dari skenario realistis di sini: file DB / file
backup bocor. Bila `cryptography` (Fernet/AES-GCM) tersedia di masa depan, modul
ini bisa ditingkatkan tanpa mengubah pemanggil.
"""
import base64
import hashlib
import hmac
import os
import secrets

_PREFIX = "sb1:"
_NONCE_LEN = 16
_MAC_LEN = 32


def _key_material() -> bytes | None:
    """Bahan kunci mentah dari env. None bila tidak ada (mis. lingkungan test)."""
    raw = os.getenv("VILOG_SECRET_KEY") or os.getenv("TOKEN") or ""
    raw = raw.strip()
    return raw.encode("utf-8") if raw else None


def _derive_key() -> bytes | None:
    mat = _key_material()
    if not mat:
        return None
    # Domain separation agar kunci ini beda dari pemakaian TOKEN lain.
    return hashlib.sha256(b"vilog-secret-box-v1|" + mat).digest()


def enabled() -> bool:
    """True bila ada kunci -> enkripsi aktif."""
    return _derive_key() is not None


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:length])


def is_encrypted(value) -> bool:
    return isinstance(value, str) and value.startswith(_PREFIX)


def encrypt(plaintext) -> str:
    """Enkripsi string. Return token "sb1:...".

    - Input kosong/None -> "" (tidak ada yang perlu dilindungi).
    - Tanpa kunci (env tak diset) -> kembalikan plaintext apa adanya supaya bot
      tetap berfungsi; startup akan memberi peringatan.
    - Sudah terenkripsi -> dikembalikan apa adanya (idempoten).
    """
    if plaintext is None or plaintext == "":
        return ""
    text = str(plaintext)
    if is_encrypted(text):
        return text
    key = _derive_key()
    if key is None:
        return text
    nonce = secrets.token_bytes(_NONCE_LEN)
    data = text.encode("utf-8")
    ct = bytes(b ^ k for b, k in zip(data, _keystream(key, nonce, len(data))))
    mac = hmac.new(key, nonce + ct, hashlib.sha256).digest()
    return _PREFIX + base64.b64encode(nonce + ct + mac).decode("ascii")


def decrypt(value) -> str:
    """Dekripsi token "sb1:...". Nilai non-token dikembalikan apa adanya.

    Backward-compat: baris lama yang masih plaintext (tanpa prefix) lewat begitu
    saja. Bila verifikasi MAC gagal (kunci salah/berubah) -> return "" agar tidak
    menampilkan data rusak; di-print sebagai peringatan.
    """
    if value is None or value == "":
        return ""
    text = str(value)
    if not is_encrypted(text):
        return text  # plaintext lama / nilai biasa
    key = _derive_key()
    if key is None:
        print("[secret_box] Tidak ada kunci untuk dekripsi (VILOG_SECRET_KEY/TOKEN kosong).")
        return ""
    try:
        blob = base64.b64decode(text[len(_PREFIX):].encode("ascii"))
    except Exception:
        return ""
    if len(blob) < _NONCE_LEN + _MAC_LEN:
        return ""
    nonce = blob[:_NONCE_LEN]
    mac = blob[-_MAC_LEN:]
    ct = blob[_NONCE_LEN:-_MAC_LEN]
    expected = hmac.new(key, nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        print("[secret_box] Verifikasi MAC gagal — kunci berbeda dari saat enkripsi?")
        return ""
    pt = bytes(b ^ k for b, k in zip(ct, _keystream(key, nonce, len(ct))))
    try:
        return pt.decode("utf-8")
    except Exception:
        return ""
