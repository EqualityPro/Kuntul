"""Entry point Admin Panel.

Dijalankan via `python -m admin` (lihat main.py -> start_admin_panel).
"""
import os

from admin.app import app, ADMIN_BRAND, ADMIN_PASSWORD

if __name__ == "__main__":
    port = int(os.environ.get("ADMIN_PORT", 5000))
    print(f"[ADMIN] {ADMIN_BRAND} Panel berjalan di http://localhost:{port}")
    print(f"[ADMIN] Password: {ADMIN_PASSWORD}")
    app.run(host="0.0.0.0", port=port, debug=False)
