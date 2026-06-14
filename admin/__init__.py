"""Paket Admin Panel (Flask).

Sebelumnya berupa file-file `admin_*.py` datar di root proyek. Kini dikemas
sebagai paket `admin/` agar rapi seperti `cogs/`. Modul utama: admin/app.py.
Jalankan dengan: `python -m admin`.

Re-export `app`, `render_page`, dan `ICONS` supaya pola lama yang dipakai banyak
blueprint, yaitu `from admin import render_page` (impor lazy di dalam fungsi),
tetap berfungsi tanpa perlu diubah.
"""
from admin.app import app, render_page, ICONS  # noqa: F401
