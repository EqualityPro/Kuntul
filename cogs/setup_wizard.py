"""Setup Wizard — konfigurasi bot lewat Discord (tanpa edit .env manual).

Masalah yang diselesaikan ("config sprawl"): bot punya puluhan ID channel/role
yang harus diisi di .env. Untuk self-host, menyalin-tempel puluhan ID 19 digit
itu melelahkan & rawan salah.

Solusi: jalankan `!setup` (atau `/setup`) lalu pilih channel/role lewat dropdown
NATIVE Discord (ChannelSelect / RoleSelect). Nilai disimpan ke tabel `settings`
(utils.settings_store) dan ditimpa ke os.environ oleh utils.config saat startup,
sehingga seluruh kode lama tetap berfungsi tanpa diubah.

Catatan bootstrap: `!setup` (prefix) sengaja disediakan karena slash command
butuh GUILD_ID untuk sync — pada server yang belum dikonfigurasi GUILD_ID bisa
kosong, jadi slash belum tersedia. Prefix command selalu bisa dipakai.
"""
import discord
from discord import app_commands
from discord.ext import commands

from utils import settings_store
from utils import config as cfg

COLOR = 0x7C6AFF
COLOR_OK = 0x2ECC71
COLOR_WARN = 0xFFA500

# Tipe channel untuk tiap kebutuhan (dipakai ChannelSelect.channel_types).
_TEXT = [discord.ChannelType.text, discord.ChannelType.news]
_VOICE = [discord.ChannelType.voice]
_CATEGORY = [discord.ChannelType.category]


class Field:
    """Satu setting yang bisa dikonfigurasi lewat wizard."""

    def __init__(self, key, label, kind, required=False, channel_types=None, help=""):
        self.key = key
        self.label = label
        self.kind = kind  # channel | category | voice | role | guild | text | int | bool
        self.required = required
        self.channel_types = channel_types or _TEXT
        self.help = help


# ── Registry: dikelompokkan supaya tiap dropdown <= 25 opsi ──────────────────
GROUPS = [
    ("🔴 Wajib", "ID inti yang dibutuhkan bot agar berfungsi normal.", [
        Field("GUILD_ID", "Server (Guild)", "guild", required=True,
              help="Server tempat bot beroperasi"),
        Field("ADMIN_ROLE_ID", "Role Admin", "role", required=True),
        Field("TICKET_CATEGORY_ID", "Kategori Tiket", "category", required=True),
        Field("MIDMAN_CHANNEL_ID", "Channel Midman", "channel", required=True),
        Field("LOG_CHANNEL_ID", "Channel Log", "channel", required=True),
        Field("TRANSCRIPT_CHANNEL_ID", "Channel Transcript", "channel", required=True),
        Field("BACKUP_CHANNEL_ID", "Channel Backup DB", "channel", required=True),
        Field("ERROR_LOG_CHANNEL_ID", "Channel Error Log", "channel", required=True),
        Field("ROBUX_CATALOG_CHANNEL_ID", "Katalog Robux", "channel", required=True),
        Field("ML_CATALOG_CHANNEL_ID", "Katalog ML", "channel", required=True),
        Field("STORE_NAME", "Nama Toko", "text", required=True,
              help="Dipakai di semua embed/footer (rebranding)"),
    ]),
    ("💳 Pembayaran & Info", "Nomor pembayaran yang ditampilkan ke pembeli.", [
        Field("DANA_NUMBER", "Nomor DANA", "text"),
        Field("BCA_NUMBER", "Nomor BCA", "text"),
    ]),
    ("📢 Channel Opsional", "Fitur yang nonaktif bila channel-nya kosong.", [
        Field("VILOG_CHANNEL_ID", "Vilog", "channel"),
        Field("VILOG_CATALOG_CHANNEL_ID", "Katalog Vilog", "channel"),
        Field("TESTIMONI_CHANNEL_ID", "Testimoni / Rating", "channel"),
        Field("WARRANTY_CHANNEL_ID", "Klaim Garansi", "channel"),
        Field("DAILY_REPORT_CHANNEL_ID", "Laporan Harian", "channel"),
        Field("LAINNYA_AUTOREPLY_CHANNEL_ID", "Auto-reply Lainnya", "channel"),
        Field("LAINNYA_CATALOG_CHANNEL_ID", "Katalog Lainnya", "channel"),
        Field("GP_CATALOG_CHANNEL_ID", "Katalog GP", "channel"),
        Field("FAQ_CHANNEL_ID", "FAQ", "channel"),
        Field("AUTOCS_CHANNEL_ID", "Auto-CS", "channel"),
        Field("FEEDBACK_CHANNEL_ID", "Saran/Masukan", "channel"),
        Field("PUBLIC_QUEUE_CHANNEL_ID", "Papan Antrian Publik", "channel"),
        Field("CUSTOMER_INSIGHT_CHANNEL_ID", "Insight Pelanggan", "channel"),
        Field("ADMIN_STATS_CHANNEL_ID", "Statistik Admin", "channel"),
        Field("GENERAL_CHANNEL_ID", "General", "channel"),
        Field("OWO_STOK_CHANNEL_ID", "Stok OwO", "channel"),
        Field("STATUS_VOICE_CHANNEL_ID", "Voice Status Toko", "voice",
              channel_types=_VOICE),
    ]),
    ("👥 Role", "Role yang dipakai berbagai fitur.", [
        Field("BOOST_ROLE_ID", "Role Booster", "role"),
        Field("CUSTOMER_ROLE_ID", "Role Customer", "role"),
        Field("TOP_SPENDER_ROLE_ID", "Role Top Spender", "role"),
        Field("OWO_NOTIF_ROLE_ID", "Role Notif OwO", "role"),
        Field("REVIEWER_BADGE_ROLE_ID", "Role Badge Reviewer", "role"),
    ]),
    ("⚙️ Angka & Saklar", "Pengaturan numerik & on/off.", [
        Field("MAX_TICKETS_PER_SERVICE", "Maks tiket aktif / layanan", "int",
              help="Default 5"),
        Field("WARRANTY_DEFAULT_DAYS", "Masa garansi default (hari)", "int",
              help="Default 7"),
        Field("SUB_FOLLOWUP_LEAD_DAYS", "Lead follow-up langganan (hari)", "int",
              help="Default 3"),
        Field("REVIEWER_BADGE_THRESHOLD", "Ambang badge reviewer", "int",
              help="Default 3"),
        Field("USE_CUSTOM_EMOJI", "Pakai custom emoji server", "bool",
              help="Nonaktifkan di server tanpa emoji custom Cellyn"),
    ]),
]

FIELDS_BY_KEY = {f.key: f for g in GROUPS for f in g[2]}
REQUIRED_FIELDS = [f for g in GROUPS for f in g[2] if f.required]


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y")


def _effective(key):
    """Nilai efektif sebuah key: setting wizard bila ada, jika tidak dari config."""
    raw = settings_store.get_setting(key)
    if raw is not None and str(raw).strip() != "":
        return raw
    return getattr(cfg, key, None)


def _is_configured(field) -> bool:
    """Apakah field sudah punya nilai 'bermakna' (bukan 0 / kosong)?"""
    val = _effective(field.key)
    if val is None:
        return False
    if field.kind in ("channel", "category", "voice", "role", "guild"):
        try:
            return int(val) != 0
        except (TypeError, ValueError):
            return False
    if field.kind == "bool":
        return True  # boolean selalu punya nilai
    return str(val).strip() != ""


def _display(field, guild) -> str:
    """String tampilan nilai sekarang (mention bila bisa di-resolve)."""
    val = _effective(field.key)
    if field.kind in ("channel", "category", "voice", "guild"):
        try:
            cid = int(val)
        except (TypeError, ValueError):
            cid = 0
        if not cid:
            return "— belum diatur"
        if field.kind == "guild":
            extra = f" — {guild.name}" if guild and guild.id == cid else ""
            return f"`{cid}`{extra}"
        ch = guild.get_channel(cid) if guild else None
        return ch.mention if ch else f"`{cid}` ⚠️ (tak ada di server ini)"
    if field.kind == "role":
        try:
            rid = int(val)
        except (TypeError, ValueError):
            rid = 0
        if not rid:
            return "— belum diatur"
        role = guild.get_role(rid) if guild else None
        return role.mention if role else f"`{rid}` ⚠️ (tak ada di server ini)"
    if field.kind == "bool":
        return "✅ Aktif" if _truthy(val) else "❌ Nonaktif"
    if val is None or str(val).strip() == "":
        return "— belum diatur"
    return f"`{val}`"


def _save(field, value):
    """Simpan nilai field & terapkan ulang config (best-effort)."""
    if value is None or str(value).strip() == "":
        settings_store.delete_setting(field.key)
    else:
        settings_store.set_setting(field.key, value)
    try:
        cfg.refresh()
    except Exception:
        pass


# ── Embeds ───────────────────────────────────────────────────────────────────
def overview_embed(guild) -> discord.Embed:
    done_req = sum(1 for f in REQUIRED_FIELDS if _is_configured(f))
    total_req = len(REQUIRED_FIELDS)
    emb = discord.Embed(
        title="🧩 Setup Wizard",
        description=(
            "Pilih kategori di bawah, lalu atur tiap nilai lewat dropdown.\n"
            "Tidak perlu menyalin ID — cukup pilih channel/role langsung.\n\n"
            f"**Progres wajib:** {done_req}/{total_req} terisi"
        ),
        color=COLOR_OK if done_req == total_req else COLOR_WARN,
    )
    for name, desc, fields in GROUPS:
        done = sum(1 for f in fields if _is_configured(f))
        emb.add_field(name=name, value=f"{desc}\n`{done}/{len(fields)} terisi`",
                      inline=False)
    missing = [f.label for f in REQUIRED_FIELDS if not _is_configured(f)]
    if missing:
        emb.add_field(
            name="⚠️ Wajib belum diisi",
            value=", ".join(missing)[:1024], inline=False)
    emb.set_footer(text="Perubahan tersimpan otomatis • restart bot agar berlaku penuh")
    return emb


def group_embed(guild, gi, note=None) -> discord.Embed:
    name, desc, fields = GROUPS[gi]
    emb = discord.Embed(title=f"{name}", description=desc, color=COLOR)
    for f in fields:
        flag = "🔴 " if f.required and not _is_configured(f) else ""
        emb.add_field(name=f"{flag}{f.label}", value=_display(f, guild), inline=False)
    if note:
        emb.add_field(name="\u200b", value=note, inline=False)
    emb.set_footer(text="Pilih setting di dropdown untuk mengubahnya")
    return emb


# ── Views ─────────────────────────────────────────────────────────────────────
class _BaseView(discord.ui.View):
    def __init__(self, guild, author_id, timeout=300):
        super().__init__(timeout=timeout)
        self.guild = guild
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Ini sesi setup milik orang lain. Jalankan `!setup` sendiri ya.",
                ephemeral=True)
            return False
        return True


class OverviewView(_BaseView):
    def __init__(self, guild, author_id):
        super().__init__(guild, author_id)
        self.add_item(_GroupSelect(self))

    @discord.ui.button(label="Sinkronkan slash command", emoji="🔄",
                       style=discord.ButtonStyle.secondary, row=1)
    async def sync_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        gid = getattr(cfg, "GUILD_ID", 0)
        if not gid:
            await interaction.response.send_message(
                "Atur **Server (Guild)** dulu di kategori 🔴 Wajib.", ephemeral=True)
            return
        try:
            obj = discord.Object(id=int(gid))
            interaction.client.tree.copy_global_to(guild=obj)
            synced = await interaction.client.tree.sync(guild=obj)
            await interaction.response.send_message(
                f"✅ {len(synced)} slash command disinkronkan ke server ini.",
                ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"⚠️ Gagal sync: `{e}`. Restart bot sebagai alternatif.",
                ephemeral=True)


class _GroupSelect(discord.ui.Select):
    def __init__(self, parent: OverviewView):
        self.parent_view = parent
        options = [
            discord.SelectOption(label=name, value=str(i), description=desc[:90])
            for i, (name, desc, _f) in enumerate(GROUPS)
        ]
        super().__init__(placeholder="Pilih kategori pengaturan…", options=options)

    async def callback(self, interaction: discord.Interaction):
        gi = int(self.values[0])
        view = GroupView(self.parent_view.guild, self.parent_view.author_id, gi)
        await interaction.response.edit_message(
            embed=group_embed(self.parent_view.guild, gi), view=view)


class GroupView(_BaseView):
    def __init__(self, guild, author_id, gi):
        super().__init__(guild, author_id)
        self.gi = gi
        self.add_item(_FieldSelect(self))

    @discord.ui.button(label="Kembali", emoji="⬅️", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=overview_embed(self.guild), view=OverviewView(self.guild, self.author_id))

    async def rerender(self, interaction: discord.Interaction, note=None):
        await interaction.response.edit_message(
            embed=group_embed(self.guild, self.gi, note=note),
            view=GroupView(self.guild, self.author_id, self.gi))


class _FieldSelect(discord.ui.Select):
    def __init__(self, parent: GroupView):
        self.parent_view = parent
        _name, _desc, fields = GROUPS[parent.gi]
        options = []
        for f in fields:
            options.append(discord.SelectOption(
                label=f.label[:100], value=f.key,
                description=(("WAJIB • " if f.required else "") + (f.help or f.kind))[:90],
                emoji=("🔴" if f.required and not _is_configured(f) else None),
            ))
        super().__init__(placeholder="Pilih yang mau diubah…", options=options)

    async def callback(self, interaction: discord.Interaction):
        field = FIELDS_BY_KEY[self.values[0]]
        await _open_editor(interaction, self.parent_view, field)


async def _open_editor(interaction, group_view: GroupView, field: Field):
    """Tampilkan editor sesuai tipe field (edit pesan yang sama)."""
    guild = group_view.guild
    emb = discord.Embed(
        title=f"Atur: {field.label}",
        description=(field.help + "\n\n" if field.help else "")
        + f"**Nilai sekarang:** {_display(field, guild)}",
        color=COLOR,
    )

    if field.kind in ("channel", "category", "voice"):
        view = EditorView(group_view, field)
        view.add_item(_ChannelPicker(group_view, field))
        await interaction.response.edit_message(embed=emb, view=view)
    elif field.kind == "role":
        view = EditorView(group_view, field)
        view.add_item(_RolePicker(group_view, field))
        await interaction.response.edit_message(embed=emb, view=view)
    elif field.kind == "guild":
        await interaction.response.edit_message(
            embed=emb, view=GuildEditorView(group_view, field))
    elif field.kind == "bool":
        await interaction.response.edit_message(
            embed=emb, view=BoolEditorView(group_view, field))
    else:  # text / int -> tombol buka modal
        await interaction.response.edit_message(
            embed=emb, view=TextEditorView(group_view, field))


class EditorView(_BaseView):
    """View editor dengan tombol simpan-clear & kembali ke grup."""

    def __init__(self, group_view: GroupView, field: Field):
        super().__init__(group_view.guild, group_view.author_id)
        self.group_view = group_view
        self.field = field

    @discord.ui.button(label="Kosongkan (reset)", emoji="🗑️",
                       style=discord.ButtonStyle.danger, row=2)
    async def clear_btn(self, interaction, button):
        _save(self.field, None)
        await self.group_view.rerender(
            interaction, note=f"🗑️ **{self.field.label}** direset ke default.")

    @discord.ui.button(label="Kembali", emoji="⬅️",
                       style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction, button):
        await self.group_view.rerender(interaction)


class _ChannelPicker(discord.ui.ChannelSelect):
    def __init__(self, group_view: GroupView, field: Field):
        self.group_view = group_view
        self.field = field
        super().__init__(placeholder=f"Pilih {field.label}…",
                         channel_types=field.channel_types, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        _save(self.field, self.values[0].id)
        await self.group_view.rerender(
            interaction, note=f"✅ **{self.field.label}** → <#{self.values[0].id}>")


class _RolePicker(discord.ui.RoleSelect):
    def __init__(self, group_view: GroupView, field: Field):
        self.group_view = group_view
        self.field = field
        super().__init__(placeholder=f"Pilih {field.label}…",
                         min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        _save(self.field, self.values[0].id)
        await self.group_view.rerender(
            interaction, note=f"✅ **{self.field.label}** → <@&{self.values[0].id}>")


class GuildEditorView(EditorView):
    @discord.ui.button(label="Gunakan server ini", emoji="🏠",
                       style=discord.ButtonStyle.success, row=0)
    async def use_here(self, interaction: discord.Interaction, button):
        gid = interaction.guild.id if interaction.guild else None
        _save(self.field, gid)
        await self.group_view.rerender(
            interaction, note=f"✅ **{self.field.label}** → `{gid}`")


class BoolEditorView(EditorView):
    @discord.ui.button(label="Aktifkan", emoji="✅",
                       style=discord.ButtonStyle.success, row=0)
    async def on_btn(self, interaction, button):
        _save(self.field, "true")
        await self.group_view.rerender(
            interaction, note=f"✅ **{self.field.label}** diaktifkan.")

    @discord.ui.button(label="Nonaktifkan", emoji="🚫",
                       style=discord.ButtonStyle.secondary, row=0)
    async def off_btn(self, interaction, button):
        _save(self.field, "false")
        await self.group_view.rerender(
            interaction, note=f"❌ **{self.field.label}** dinonaktifkan.")


class TextEditorView(EditorView):
    @discord.ui.button(label="Isi / ubah nilai", emoji="✏️",
                       style=discord.ButtonStyle.primary, row=0)
    async def edit_btn(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(_TextModal(self.group_view, self.field))


class _TextModal(discord.ui.Modal):
    def __init__(self, group_view: GroupView, field: Field):
        super().__init__(title=f"Atur {field.label}"[:45])
        self.group_view = group_view
        self.field = field
        current = settings_store.get_setting(field.key) or ""
        self.inp = discord.ui.TextInput(
            label=field.label[:45],
            default=str(current)[:200],
            required=False,
            max_length=200,
            placeholder=(field.help or "Kosongkan untuk reset ke default")[:100],
        )
        self.add_item(self.inp)

    async def on_submit(self, interaction: discord.Interaction):
        val = str(self.inp.value).strip()
        if self.field.kind == "int" and val != "":
            try:
                int(val)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Nilai harus berupa angka.", ephemeral=True)
                return
        _save(self.field, val if val != "" else None)
        note = (f"✅ **{self.field.label}** disimpan." if val
                else f"🗑️ **{self.field.label}** direset ke default.")
        try:
            await self.group_view.rerender(interaction, note=note)
        except discord.HTTPException:
            await interaction.response.send_message(note, ephemeral=True)


# ── Cog ────────────────────────────────────────────────────────────────────────
class SetupWizard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _can_manage(member) -> bool:
        perms = getattr(member, "guild_permissions", None)
        if perms and (perms.administrator or perms.manage_guild):
            return True
        admin_role_id = getattr(cfg, "ADMIN_ROLE_ID", 0)
        if admin_role_id and any(r.id == admin_role_id
                                 for r in getattr(member, "roles", [])):
            return True
        return False

    @commands.command(name="setup")
    async def setup_prefix(self, ctx: commands.Context):
        """Buka Setup Wizard (prefix — selalu tersedia walau slash belum sync)."""
        if ctx.guild is None:
            await ctx.send("Jalankan perintah ini di dalam server.")
            return
        if not self._can_manage(ctx.author):
            await ctx.send("❌ Butuh izin **Manage Server** atau role admin.")
            return
        view = OverviewView(ctx.guild, ctx.author.id)
        await ctx.send(embed=overview_embed(ctx.guild), view=view)

    @app_commands.command(name="setup",
                          description="Konfigurasi bot lewat dropdown (admin)")
    async def setup_slash(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "Jalankan perintah ini di dalam server.", ephemeral=True)
            return
        if not self._can_manage(interaction.user):
            await interaction.response.send_message(
                "❌ Butuh izin **Manage Server** atau role admin.", ephemeral=True)
            return
        view = OverviewView(interaction.guild, interaction.user.id)
        await interaction.response.send_message(
            embed=overview_embed(interaction.guild), view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupWizard(bot))
    print("Cog SetupWizard siap.")
