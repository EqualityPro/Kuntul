"""Admin panel: kelola komplain/refund customer + rekap (Blueprint).

Data dari utils.complaints. Customer mengajukan via /komplain (cogs/complaints).
"""
import html as _h

from flask import Blueprint, flash, redirect, request, session, url_for

from utils import complaints as cp

complaints_bp = Blueprint("complaints_bp", __name__)

STATUS_LABEL = {
    "baru": ("Baru", "var(--warning)"),
    "diproses": ("Diproses", "var(--accent)"),
    "selesai": ("Selesai", "var(--success)"),
    "ditolak": ("Ditolak", "var(--danger)"),
}


def _badge(s):
    label, color = STATUS_LABEL.get(s, (s, "var(--muted)"))
    return (f'<span class="badge" style="background:color-mix(in srgb,{color} 16%,'
            f'transparent);color:{color};">{label}</span>')



@complaints_bp.route("/complaints")
def page_complaints():
    if not session.get("logged_in"):
        return redirect("/login")
    from admin import render_page
    cp.init_complaints()
    flt = request.args.get("status", "").strip().lower()
    if flt not in cp.STATUSES:
        flt = ""
    items = cp.list_complaints(status=flt or None)
    st = cp.stats()

    def _tab(key, text):
        on = "btn-primary" if (flt == key or (key == "" and not flt)) else "btn-ghost"
        href = "/complaints?status=" + key if key else "/complaints"
        return f'<a href="{href}" class="btn {on} btn-sm">{text}</a>'

    tabs = (
        _tab("", f"Semua ({st['total']})")
        + _tab("baru", f"Baru ({st['by_status']['baru']})")
        + _tab("diproses", f"Diproses ({st['by_status']['diproses']})")
        + _tab("selesai", f"Selesai ({st['by_status']['selesai']})")
        + _tab("ditolak", f"Ditolak ({st['by_status']['ditolak']})")
    )

    rows = ""
    for c in items:
        when = (c["created_at"] or "")[:16].replace("T", " ")
        user = _h.escape(c["username"] or str(c["user_id"]))
        detail = _h.escape((c["detail"] or "")[:200])
        order = _h.escape(c["related_order"] or "-")
        note = _h.escape(c["admin_note"] or "")
        rows += f"""<tr>
          <td>#{c['id']}</td>
          <td style="color:var(--muted);white-space:nowrap;">{when}</td>
          <td>{user}</td>
          <td>{_h.escape(c['category'] or '')}</td>
          <td style="max-width:280px;">{detail}</td>
          <td>{order}</td>
          <td>{_badge(c['status'])}</td>
          <td><div style="display:flex;gap:.3rem;flex-wrap:wrap;">
            <form method="POST" action="/complaints/status/{c['id']}"><input type="hidden" name="status" value="diproses"><button class="btn btn-sm btn-warn">Proses</button></form>
            <form method="POST" action="/complaints/status/{c['id']}"><input type="hidden" name="status" value="selesai"><button class="btn btn-sm btn-success">Selesai</button></form>
            <form method="POST" action="/complaints/status/{c['id']}"><input type="hidden" name="status" value="ditolak"><button class="btn btn-sm btn-danger">Tolak</button></form>
          </div>
          <form method="POST" action="/complaints/note/{c['id']}" class="inline-form" style="margin-top:.35rem;">
            <input name="note" value="{note}" placeholder="catatan admin..." style="flex:1;min-width:120px;padding:.35rem .5rem;background:var(--surface);border:1px solid var(--border2);border-radius:7px;color:var(--text);font-size:.78rem;">
            <button class="btn btn-ghost btn-sm">Simpan</button>
          </form></td>
        </tr>"""
    if not rows:
        rows = '<tr><td colspan="8" class="empty">Belum ada komplain.</td></tr>'

    cat_recap = "".join(
        f"<li style='margin:.25rem 0;'>{_h.escape(cat)} — <b>{n}</b></li>"
        for cat, n in st["by_category"]
    ) or "<li style='color:var(--muted);'>Belum ada data.</li>"


    content = f"""
<div class="page-header">
  <div class="page-title">Komplain &amp; Refund<small>Kelola pengaduan customer</small></div>
</div>
<div class="stats-grid">
  <div class="stat-card gold"><div class="stat-label">Total</div><div class="stat-value">{st['total']}</div></div>
  <div class="stat-card ff"><div class="stat-label">Terbuka</div><div class="stat-value">{st['open']}</div></div>
  <div class="stat-card green"><div class="stat-label">Selesai</div><div class="stat-value">{st['by_status']['selesai']}</div></div>
  <div class="stat-card robux"><div class="stat-label">Ditolak</div><div class="stat-value">{st['by_status']['ditolak']}</div></div>
</div>
<div class="card"><div class="card-body" style="display:flex;gap:.4rem;flex-wrap:wrap;align-items:center;">{tabs}</div></div>
<div class="card">
  <div class="card-header"><span class="card-title">Daftar Komplain</span></div>
  <div class="table-wrapper">
    <table>
      <thead><tr><th>ID</th><th>Tanggal</th><th>User</th><th>Kategori</th><th>Detail</th><th>Order</th><th>Status</th><th>Aksi</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>
<div class="card">
  <div class="card-header"><span class="card-title">Rekap per Kategori</span></div>
  <div class="card-body"><ul style="list-style:none;padding:0;margin:0;font-size:.88rem;">{cat_recap}</ul></div>
</div>
"""
    return render_page(content)


@complaints_bp.route("/complaints/status/<int:cid>", methods=["POST"])
def complaints_set_status(cid):
    if not session.get("logged_in"):
        return redirect("/login")
    status = request.form.get("status", "").strip().lower()
    if cp.set_status(cid, status):
        flash(f"Komplain #{cid} → {status}.", "success")
    else:
        flash("Status tidak valid.", "error")
    return redirect(request.referrer or url_for("complaints_bp.page_complaints"))


@complaints_bp.route("/complaints/note/<int:cid>", methods=["POST"])
def complaints_set_note(cid):
    if not session.get("logged_in"):
        return redirect("/login")
    cp.set_admin_note(cid, request.form.get("note", "").strip())
    flash(f"Catatan komplain #{cid} disimpan.", "success")
    return redirect(request.referrer or url_for("complaints_bp.page_complaints"))
