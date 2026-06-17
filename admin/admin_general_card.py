"""admin_general_card.py - Editor Kartu Umum "Order Selesai" untuk Admin Panel.

Blueprint terpisah (pola sama dgn admin_rating_theme.py). Memberi editor visual
untuk KARTU UMUM yang dilampirkan ke pesan log transaksi saat order selesai tapi
buyer TIDAK membuka badge baru (render_general_card di cogs/profile.py):
  - /general-card            : halaman editor (drag-drop posisi + warna/font/teks)
  - /general-card/preview.png: render kartu contoh dgn tema saat ini
  - /general-card/save       : simpan tema (POST JSON)
  - /general-card/reset      : kembalikan ke default
  - /general-card/font       : upload file font .ttf/.otf (POST file)
  - /general-card/bg         : upload background (POST file)
  - /general-card/bg/delete  : hapus background

Background tunggal: data/generalcardbg.<ext>. Font kustom: data/general_font.<ext>.
render_page di-import lazily di dalam view (hindari circular import).
"""
import os
import json

from flask import Blueprint, request, session, redirect, Response, jsonify

from utils import general_card_theme as gcthemelib
from utils import card_presets

general_card_bp = Blueprint("general_card_bp", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ALLOWED_FONT_EXTS = (".ttf", ".otf")
ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
GENERAL_BG_BASE = "generalcardbg"
GENERAL_ICON_BASE = "general_icon"

SAMPLE_PRODUCT = "Robux 1000"

# Contoh nilai elemen dinamis untuk pratinjau editor (data asli berasal dari
# transaksi/profil saat bot mengirim kartu).
SAMPLE_VALUES = {
    "layanan": "Robux",
    "harga": "Rp 50.000",
    "qty": "1x",
    "tanggal": "17/06/2026",
    "seller": "AdminToko",
    "order_no": "#1234",
    "rating": "5/5",
    "_stars_filled": 5,
    "tier": "GOLD",
    "level": "Level 7",
    "total_orders": "Order ke-12",
    "total_spent": "Total Rp 1.450.000",
    "spent_month": "Bulan ini Rp 540.000",
    "total_reviews": "3 ulasan",
    "member_since": "Member sejak Mei 2025",
    "topspender": "#1 Top Spender",
}


def _bg_path():
    for ext in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, GENERAL_BG_BASE + ext)
        if os.path.exists(p):
            return p
    return None


def _icon_path():
    for ext in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, GENERAL_ICON_BASE + ext)
        if os.path.exists(p):
            return p
    return None


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@general_card_bp.route("/general-card/preview.png")
def preview_png():
    g = _guard()
    if g:
        return g
    raw = request.args.get("t")
    theme = gcthemelib.merge_theme(raw) if raw else gcthemelib.load_theme()
    name = (request.args.get("name") or "").strip() or "ContohMember"
    product = (request.args.get("product") or "").strip() or SAMPLE_PRODUCT
    values = dict(SAMPLE_VALUES)
    values["name"] = name
    values["product"] = product
    try:
        from cogs.profile import render_general_card
        buf = render_general_card(None, values=values, theme=theme,
                                  bg_path=_bg_path(), icon_path=_icon_path())
        return Response(buf.getvalue(), mimetype="image/png")
    except Exception as e:
        png_1x1 = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                   b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
                   b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        return Response(png_1x1, mimetype="image/png",
                        headers={"X-Render-Error": str(e)[:200]})


@general_card_bp.route("/general-card/save", methods=["POST"])
def save_theme_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    if "font_file" not in payload:
        payload["font_file"] = gcthemelib.load_theme().get("font_file")
    theme = gcthemelib.save_theme(payload)
    return jsonify({"ok": True, "theme": theme})


@general_card_bp.route("/general-card/reset", methods=["POST"])
def reset_theme_route():
    g = _guard()
    if g:
        return g
    theme = gcthemelib.save_theme(gcthemelib.default_theme())
    return jsonify({"ok": True, "theme": theme})


@general_card_bp.route("/general-card/font", methods=["POST"])
def upload_font():
    g = _guard()
    if g:
        return g
    f = request.files.get("font")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "Tidak ada file."}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_FONT_EXTS:
        return jsonify({"ok": False, "error": "Format harus .ttf atau .otf."}), 400
    os.makedirs(DATA_DIR, exist_ok=True)
    fname = "general_font" + ext
    for e in ALLOWED_FONT_EXTS:
        old = os.path.join(DATA_DIR, "general_font" + e)
        if os.path.exists(old) and e != ext:
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, fname))
    theme = gcthemelib.load_theme()
    theme["font_file"] = fname
    gcthemelib.save_theme(theme)
    return jsonify({"ok": True, "font_file": fname})


@general_card_bp.route("/general-card/bg", methods=["POST"])
def upload_bg():
    g = _guard()
    if g:
        return g
    f = request.files.get("bg")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "Tidak ada file."}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({"ok": False, "error": "Format harus PNG/JPG/WEBP."}), 400
    os.makedirs(DATA_DIR, exist_ok=True)
    for e in ALLOWED_IMAGE_EXTS:
        old = os.path.join(DATA_DIR, GENERAL_BG_BASE + e)
        if os.path.exists(old):
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, GENERAL_BG_BASE + ext))
    return jsonify({"ok": True, "has_bg": True})


@general_card_bp.route("/general-card/bg/delete", methods=["POST"])
def delete_bg():
    g = _guard()
    if g:
        return g
    removed = False
    for e in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, GENERAL_BG_BASE + e)
        if os.path.exists(p):
            try:
                os.remove(p)
                removed = True
            except Exception:
                pass
    return jsonify({"ok": True, "removed": removed, "has_bg": False})


@general_card_bp.route("/general-card/icon", methods=["POST"])
def upload_icon():
    g = _guard()
    if g:
        return g
    f = request.files.get("icon")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "Tidak ada file."}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({"ok": False, "error": "Format harus PNG/JPG/WEBP."}), 400
    os.makedirs(DATA_DIR, exist_ok=True)
    for e in ALLOWED_IMAGE_EXTS:
        old = os.path.join(DATA_DIR, GENERAL_ICON_BASE + e)
        if os.path.exists(old):
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, GENERAL_ICON_BASE + ext))
    return jsonify({"ok": True, "has_icon": True})


@general_card_bp.route("/general-card/icon/delete", methods=["POST"])
def delete_icon():
    g = _guard()
    if g:
        return g
    removed = False
    for e in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, GENERAL_ICON_BASE + e)
        if os.path.exists(p):
            try:
                os.remove(p)
                removed = True
            except Exception:
                pass
    return jsonify({"ok": True, "removed": removed, "has_icon": False})


@general_card_bp.route("/general-card")
def page_theme():
    g = _guard()
    if g:
        return g
    from admin import render_page

    theme = gcthemelib.load_theme()
    theme_json = json.dumps(theme)
    labels_json = json.dumps(dict(gcthemelib.ELEMENT_LABELS))
    order_json = json.dumps([k for k, _ in gcthemelib.ELEMENT_LABELS])
    cur_font = theme.get("font_file") or "(default sistem)"
    has_bg_json = json.dumps(_bg_path() is not None)
    has_icon_json = json.dumps(_icon_path() is not None)
    enabled_attr = "checked" if theme.get("enabled") else ""
    presets_json = json.dumps(card_presets.presets_for("general"))
    default_json = json.dumps(gcthemelib.default_theme())
    cw, ch = gcthemelib.GENERAL_W, gcthemelib.GENERAL_H

    content = f"""
<style>
.thm-tabs{{display:flex;gap:.25rem;margin-bottom:1rem;border-bottom:1px solid var(--border);flex-wrap:wrap;}}
.thm-tab{{appearance:none;background:none;border:none;border-bottom:2px solid transparent;color:var(--muted2);font:inherit;font-size:.82rem;font-weight:600;padding:.5rem .75rem;cursor:pointer;border-radius:8px 8px 0 0;}}
.thm-tab:hover{{color:var(--text);background:var(--surface2);}}
.thm-tab.active{{color:var(--accent);border-bottom-color:var(--accent);}}
@media(min-width:920px){{.thm-stage{{position:sticky;top:1.5rem;align-self:flex-start;}}}}
</style>
<div class="page-header">
  <div class="page-title">Editor Kartu Umum <small>Kartu "Order Selesai" yang dikirim saat buyer belum membuka badge baru</small></div>
</div>
<div class="card"><div class="card-body" style="display:flex;flex-wrap:wrap;gap:1.5rem;align-items:flex-start;">
  <div class="thm-stage" style="flex:1 1 560px;min-width:280px;">
    <div style="font-size:.8rem;color:var(--muted);margin-bottom:.5rem;">
      Seret kotak elemen untuk memindah posisi. Kanvas {cw}×{ch} (skala mengikuti lebar).</div>
    <div id="stage" style="position:relative;width:100%;max-width:840px;margin:0 auto;aspect-ratio:{cw}/{ch};
        border-radius:14px;overflow:hidden;border:1px solid var(--border);
        background:#222 url('/general-card/preview.png') center/cover no-repeat;user-select:none;"></div>
    <div style="display:flex;gap:.5rem;margin-top:.8rem;flex-wrap:wrap;">
      <button class="btn btn-primary" onclick="saveTheme()">Simpan</button>
      <button class="btn btn-ghost" onclick="refreshPreview()">Perbarui Pratinjau</button>
      <button class="btn btn-ghost" onclick="resetTheme()">Reset Default</button>
    </div>
    <div id="status" style="margin-top:.6rem;font-size:.85rem;"></div>
  </div>
  <div class="thm-col" style="flex:1 1 320px;min-width:280px;">
    <div class="thm-tabs">
      <button type="button" class="thm-tab active" data-t="elemen" onclick="showThmTab('elemen')">Elemen</button>
      <button type="button" class="thm-tab" data-t="tampilan" onclick="showThmTab('tampilan')">Tampilan</button>
      <button type="button" class="thm-tab" data-t="aset" onclick="showThmTab('aset')">Aset</button>
    </div>
    <div class="thm-panel" id="thm-tampilan" hidden>
      <div class="form-group">
        <label style="display:flex;align-items:center;gap:.5rem;">
          <input type="checkbox" id="cardEnabled" {enabled_attr} onchange="theme.enabled=this.checked;markDirty();" style="width:auto;">
          Aktifkan kartu umum (gambar)
        </label>
        <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Jika aktif, kartu ini dilampirkan ke log transaksi tiap order selesai yang TIDAK membuka badge baru. Jika nonaktif, perilaku lama dipakai (tanpa kartu).</div>
      </div>
      <div id="cfgWarn" style="display:none;margin:0 0 .8rem;padding:.55rem .7rem;border-radius:8px;
        background:rgba(240,180,40,.12);border:1px solid rgba(240,180,40,.4);color:var(--warning);font-size:.8rem;"></div>
      <div class="form-group">
        <label>Galeri Preset (gaya warna)</label>
        <div style="display:flex;gap:.5rem;flex-wrap:wrap;">
          <select id="presetSel" style="flex:1 1 auto;min-width:160px;">
            <option value="">— pilih preset —</option>
          </select>
          <button class="btn btn-ghost btn-sm" onclick="applyPresetSel()">Terapkan</button>
        </div>
        <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Preset hanya mengubah warna &amp; opacity (posisi elemen tetap). Klik Simpan untuk menerapkan ke bot.</div>
      </div>
      <div class="form-group">
        <label>Nama Contoh (pratinjau)</label>
        <input type="text" id="sampleName" maxlength="22" placeholder="ContohMember"
          oninput="refreshPreview();" style="width:100%;">
      </div>
      <div class="form-group">
        <label>Produk Contoh (pratinjau)</label>
        <input type="text" id="sampleProduct" maxlength="40" placeholder="Robux 1000"
          oninput="refreshPreview();" style="width:100%;">
        <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Nama, avatar &amp; produk asli berasal dari transaksi, jadi pratinjau memakai contoh.</div>
      </div>
      <div class="form-group">
        <label>Opacity Panel ({theme['panel_opacity']})</label>
        <input type="range" min="0" max="255" id="panelOpacity" value="{theme['panel_opacity']}"
          oninput="theme.panel_opacity=+this.value;markDirty();">
      </div>
    </div>
    <div class="thm-panel" id="thm-aset" hidden>
      <div class="form-group">
        <label>Font Kustom — saat ini: <b id="curFont">{cur_font}</b></label>
        <input type="file" id="fontFile" accept=".ttf,.otf">
        <button class="btn btn-ghost btn-sm" style="margin-top:.4rem;" onclick="uploadFont()">Upload Font (.ttf/.otf)</button>
      </div>
      <div class="form-group">
        <label>Background Kartu <small style="color:var(--muted)" id="bgInfo"></small></label>
        <input type="file" id="bgFile" accept=".png,.jpg,.jpeg,.webp">
        <div style="display:flex;gap:.5rem;margin-top:.4rem;flex-wrap:wrap;">
          <button class="btn btn-ghost btn-sm" onclick="uploadBg()">Upload Background</button>
          <button class="btn btn-ghost btn-sm" onclick="deleteBg()">Hapus Background</button>
        </div>
        <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Tanpa background = gradien default yang kalem.</div>
      </div>
      <div class="form-group">
        <label>Logo/Ikon Toko <small style="color:var(--muted)" id="iconInfo"></small></label>
        <input type="file" id="iconFile" accept=".png,.jpg,.jpeg,.webp">
        <div style="display:flex;gap:.5rem;margin-top:.4rem;flex-wrap:wrap;">
          <button class="btn btn-ghost btn-sm" onclick="uploadIcon()">Upload Logo</button>
          <button class="btn btn-ghost btn-sm" onclick="deleteIcon()">Hapus Logo</button>
        </div>
        <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Logo dipakai elemen "Logo/Ikon Toko" (tampilkan dulu elemennya di tab Elemen).</div>
      </div>
    </div>
    <div class="thm-panel" id="thm-elemen">
      <div style="font-size:.78rem;color:var(--muted);margin-bottom:.6rem;">
        Elemen inti (foto profil, judul, nama, pesan, produk) tampil default. Elemen lain
        defaultnya <b>disembunyikan</b> biar tidak penuh — pilih elemennya lalu set "Tampilkan: Ya".
      </div>
      <label style="font-weight:600;">Elemen</label>
      <select id="elemSel" onchange="renderControls()" style="width:100%;margin:.4rem 0 .8rem;"></select>
      <div id="elemControls"></div>
    </div>
  </div>
</div></div>

<script>
var THEME = {theme_json};
var LABELS = {labels_json};
var ORDER = {order_json};
var HAS_BG = {has_bg_json};
var HAS_ICON = {has_icon_json};
var PRESETS = {presets_json};
var DEFAULT_THEME = {default_json};
var theme = JSON.parse(JSON.stringify(THEME));
var CARD_W={cw}, CARD_H={ch};

(function initPresets(){{
  var ps=document.getElementById('presetSel'); if(!ps) return;
  PRESETS.forEach(function(p){{ var o=document.createElement('option'); o.value=p.id; o.textContent=p.name; ps.appendChild(o); }});
}})();
function applyPresetSel(){{
  var ps=document.getElementById('presetSel'); if(!ps||!ps.value) return;
  var p=null; PRESETS.forEach(function(x){{ if(x.id===ps.value) p=x; }}); if(!p) return;
  if(typeof p.opacity!=='undefined' && p.opacity!==null){{ theme.panel_opacity=p.opacity; var po=document.getElementById('panelOpacity'); if(po) po.value=p.opacity; }}
  if(p.ring && theme.elements.avatar){{ theme.elements.avatar.ring_color=p.ring; }}
  if(p.colors){{ for(var k in p.colors){{ if(theme.elements[k]) theme.elements[k].color=p.colors[k]; }} }}
  renderControls(); markDirty(); setOk('Preset "'+p.name+'" diterapkan — klik Simpan untuk menyimpan.');
}}

function _stripEnabled(t){{ var c=JSON.parse(JSON.stringify(t)); c.enabled=false; return JSON.stringify(c); }}
function checkConfigured(){{
  var w=document.getElementById('cfgWarn'); if(!w) return;
  var isDefault=(_stripEnabled(theme)===_stripEnabled(DEFAULT_THEME));
  if(theme.enabled && isDefault && !HAS_BG){{
    w.style.display='block';
    w.innerHTML='\\u26A0 Kartu umum diaktifkan tapi masih tampilan default & belum ada background. Atur warna/posisi atau pilih preset dulu biar tidak terlihat generik.';
  }} else {{ w.style.display='none'; }}
}}

function showThmTab(t){{
  document.querySelectorAll('.thm-panel').forEach(function(p){{p.hidden=(p.id!=='thm-'+t);}});
  document.querySelectorAll('.thm-tab').forEach(function(b){{b.classList.toggle('active', b.dataset.t===t);}});
}}

var _previewTimer=null;
function markDirty(){{
  document.getElementById('status').innerHTML='<span style="color:var(--warning)">\\u25CF Perubahan belum disimpan (pratinjau diperbarui...)</span>';
  checkConfigured();
  if(_previewTimer) clearTimeout(_previewTimer);
  _previewTimer=setTimeout(refreshPreview, 400);
}}
function setOk(m){{ document.getElementById('status').innerHTML='<span style="color:var(--success)">\\u2713 '+m+'</span>'; checkConfigured(); }}

var sel=document.getElementById('elemSel');
ORDER.forEach(function(k){{ var o=document.createElement('option'); o.value=k; o.textContent=LABELS[k]||k; sel.appendChild(o); }});

var stage=document.getElementById('stage');
function stageScale(){{ return stage.clientWidth / CARD_W; }}

function renderBoxes(){{
  stage.querySelectorAll('.el-box').forEach(function(e){{e.remove();}});
  var sc=stageScale();
  ORDER.forEach(function(k){{
    var el=theme.elements[k]; if(!el) return;
    var box=document.createElement('div');
    box.className='el-box'; box.dataset.k=k;
    box.style.cssText='position:absolute;padding:2px 6px;font-size:11px;border-radius:6px;cursor:move;'+
      'background:rgba(90,109,196,.9);color:#fff;white-space:nowrap;'+(el.show===false?'opacity:.4;':'');
    box.style.left=(el.x*sc)+'px'; box.style.top=(el.y*sc)+'px';
    box.textContent=LABELS[k]||k;
    box.onmousedown=startDrag;
    stage.appendChild(box);
  }});
}}

var drag=null;
function startDrag(e){{
  drag={{k:e.target.dataset.k, sx:e.clientX, sy:e.clientY,
        ox:theme.elements[e.target.dataset.k].x, oy:theme.elements[e.target.dataset.k].y}};
  sel.value=drag.k; renderControls();
  document.onmousemove=onDrag; document.onmouseup=endDrag; e.preventDefault();
}}
function onDrag(e){{
  if(!drag) return; var sc=stageScale();
  var nx=Math.round(drag.ox+(e.clientX-drag.sx)/sc);
  var ny=Math.round(drag.oy+(e.clientY-drag.sy)/sc);
  var el=theme.elements[drag.k];
  el.x=Math.max(0,Math.min(CARD_W,nx)); el.y=Math.max(0,Math.min(CARD_H,ny));
  renderBoxes(); renderControls(); markDirty();
}}
function endDrag(){{ drag=null; document.onmousemove=null; document.onmouseup=null; refreshPreview(); }}

function renderControls(){{
  var k=sel.value, el=theme.elements[k]; var h='';
  h+='<div class="form-group"><label>Tampilkan</label><select onchange="theme.elements[\\''+k+'\\'].show=(this.value==\\'1\\');renderBoxes();markDirty();">'+
     '<option value="1"'+(el.show!==false?' selected':'')+'>Ya</option><option value="0"'+(el.show===false?' selected':'')+'>Sembunyikan</option></select></div>';
  if(typeof el.text!=='undefined'){{
    h+='<div class="form-group"><label>Teks</label><input type="text" maxlength="120" value="'+(el.text||'').replace(/"/g,'&quot;')+'" oninput="theme.elements[\\''+k+'\\'].text=this.value;markDirty();"></div>';
  }}
  h+='<div class="form-group"><label>X: '+el.x+'</label><input type="range" min="0" max="'+CARD_W+'" value="'+el.x+'" oninput="theme.elements[\\''+k+'\\'].x=+this.value;renderBoxes();markDirty();"></div>';
  h+='<div class="form-group"><label>Y: '+el.y+'</label><input type="range" min="0" max="'+CARD_H+'" value="'+el.y+'" oninput="theme.elements[\\''+k+'\\'].y=+this.value;renderBoxes();markDirty();"></div>';
  if(el.type==='text'){{
    h+='<div class="form-group"><label>Ukuran Font: '+el.size+'</label><input type="range" min="8" max="120" value="'+el.size+'" oninput="theme.elements[\\''+k+'\\'].size=+this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Warna</label><input type="color" value="'+el.color+'" oninput="theme.elements[\\''+k+'\\'].color=this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Tebal</label><select onchange="theme.elements[\\''+k+'\\'].bold=(this.value==\\'1\\');markDirty();"><option value="1"'+(el.bold?' selected':'')+'>Bold</option><option value="0"'+(!el.bold?' selected':'')+'>Normal</option></select></div>';
  }} else if(el.type==='avatar'){{
    h+='<div class="form-group"><label>Ukuran: '+el.size+'</label><input type="range" min="32" max="320" value="'+el.size+'" oninput="theme.elements[\\''+k+'\\'].size=+this.value;renderBoxes();markDirty();"></div>';
    h+='<div class="form-group"><label>Warna Bingkai (ring)</label><input type="color" value="'+(el.ring_color||'#3DD68C')+'" oninput="theme.elements[\\''+k+'\\'].ring_color=this.value;markDirty();"></div>';
  }} else if(el.type==='stars'){{
    h+='<div class="form-group"><label>Ukuran: '+el.size+'</label><input type="range" min="8" max="120" value="'+el.size+'" oninput="theme.elements[\\''+k+'\\'].size=+this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Warna</label><input type="color" value="'+el.color+'" oninput="theme.elements[\\''+k+'\\'].color=this.value;markDirty();"></div>';
    h+='<div class="form-group" style="font-size:.78rem;color:var(--muted)">Jumlah bintang terisi mengikuti rating asli buyer.</div>';
  }} else if(el.type==='icon'){{
    h+='<div class="form-group"><label>Ukuran: '+el.size+'</label><input type="range" min="32" max="360" value="'+el.size+'" oninput="theme.elements[\\''+k+'\\'].size=+this.value;renderBoxes();markDirty();"></div>';
    h+='<div class="form-group" style="font-size:.78rem;color:var(--muted)">Upload gambar logo di tab Aset.</div>';
  }}
  document.getElementById('elemControls').innerHTML=h;
}}

function refreshPreview(){{
  var nameEl=document.getElementById('sampleName');
  var prodEl=document.getElementById('sampleProduct');
  var nameq=(nameEl && nameEl.value.trim()) ? '&name='+encodeURIComponent(nameEl.value.trim()) : '';
  var prodq=(prodEl && prodEl.value.trim()) ? '&product='+encodeURIComponent(prodEl.value.trim()) : '';
  var url='/general-card/preview.png?t='+encodeURIComponent(JSON.stringify(theme))+nameq+prodq+'&_='+Date.now();
  stage.style.backgroundImage="url('"+url+"')";
}}
function initBgUI(){{
  document.getElementById('bgInfo').textContent = HAS_BG ? '— background terpasang \\u2713' : '— belum ada background';
}}
function initIconUI(){{
  var el=document.getElementById('iconInfo'); if(el) el.textContent = HAS_ICON ? '— logo terpasang \\u2713' : '— belum ada logo';
}}
function uploadIcon(){{
  var f=document.getElementById('iconFile').files[0];
  if(!f){{alert('Pilih file gambar dulu.');return;}}
  var fd=new FormData(); fd.append('icon',f);
  fetch('/general-card/icon',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ HAS_ICON=true; initIconUI(); setOk('Logo diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload logo.'); }}
  }});
}}
function deleteIcon(){{
  if(!confirm('Hapus logo kartu umum?')) return;
  fetch('/general-card/icon/delete',{{method:'POST'}}).then(r=>r.json()).then(function(d){{
    HAS_ICON=false; initIconUI(); setOk('Logo dihapus.'); refreshPreview(); }});
}}
function uploadBg(){{
  var f=document.getElementById('bgFile').files[0];
  if(!f){{alert('Pilih file gambar dulu.');return;}}
  var fd=new FormData(); fd.append('bg',f);
  fetch('/general-card/bg',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ HAS_BG=true; initBgUI(); setOk('Background diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload background.'); }}
  }});
}}
function deleteBg(){{
  if(!confirm('Hapus background kartu umum?')) return;
  fetch('/general-card/bg/delete',{{method:'POST'}}).then(r=>r.json()).then(function(d){{
    HAS_BG=false; initBgUI(); setOk('Background dihapus (kembali ke gradien).'); refreshPreview(); }});
}}
function saveTheme(){{
  fetch('/general-card/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(theme)}})
    .then(r=>r.json()).then(function(d){{ if(d.ok){{theme=d.theme; setOk('Tema disimpan & diterapkan ke bot.'); refreshPreview();}} else {{markDirty();}} }});
}}
function resetTheme(){{
  if(!confirm('Kembalikan ke tema default?')) return;
  fetch('/general-card/reset',{{method:'POST'}}).then(r=>r.json()).then(function(d){{
    theme=d.theme; document.getElementById('cardEnabled').checked=!!theme.enabled;
    renderBoxes(); renderControls(); refreshPreview(); setOk('Direset ke default.'); }});
}}
function uploadFont(){{
  var f=document.getElementById('fontFile').files[0];
  if(!f){{alert('Pilih file font dulu.');return;}}
  var fd=new FormData(); fd.append('font',f);
  fetch('/general-card/font',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ theme.font_file=d.font_file; document.getElementById('curFont').textContent=d.font_file; setOk('Font diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload font.'); }}
  }});
}}

window.addEventListener('resize', renderBoxes);
renderBoxes(); renderControls(); initBgUI(); initIconUI(); checkConfigured();
</script>"""
    return render_page(content)
