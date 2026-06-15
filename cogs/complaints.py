"""Komplain/Refund: customer mengajukan lewat /komplain.

Tersimpan ke tabel `complaints` (utils.complaints) & dikirim sebagai notifikasi
ke channel admin. Admin mengelola status/catatan lewat Admin Panel (/complaints).
"""
import discord
from discord import app_commands
from discord.ext import commands

from utils import complaints as cp
from utils.config import (
    STORE_NAME, LOG_CHANNEL_ID, FEEDBACK_CHANNEL_ID, COMPLAINT_CHANNEL_ID,
)

_CHOICES = [app_commands.Choice(name=c, value=c) for c in cp.CATEGORIES]


class Complaints(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="komplain",
        description="Ajukan komplain / permintaan refund ke admin",
    )
    @app_commands.describe(
        kategori="Jenis komplain",
        detail="Jelaskan masalahmu sedetail mungkin",
        order="No. order / nama channel tiket (opsional)",
    )
    @app_commands.choices(kategori=_CHOICES)
    async def komplain(
        self,
        interaction: discord.Interaction,
        kategori: app_commands.Choice[str],
        detail: str,
        order: str = "",
    ):
        cid = cp.create_complaint(
            interaction.user.id, str(interaction.user), kategori.value, detail, order
        )
        target_id = COMPLAINT_CHANNEL_ID or FEEDBACK_CHANNEL_ID or LOG_CHANNEL_ID
        ch = interaction.client.get_channel(target_id) if target_id else None
        if ch is not None:
            emb = discord.Embed(title=f"📣 Komplain Baru #{cid}", color=0xF97316)
            emb.add_field(name="Dari", value=interaction.user.mention, inline=True)
            emb.add_field(name="Kategori", value=kategori.value, inline=True)
            if order:
                emb.add_field(name="Order/Tiket", value=order[:256], inline=True)
            emb.add_field(name="Detail", value=detail[:1000], inline=False)
            emb.set_footer(text=f"{STORE_NAME} • kelola di Admin Panel → /complaints")
            try:
                await ch.send(embed=emb)
            except Exception as e:
                print(f"[Complaints] gagal kirim notif: {e}")
        await interaction.response.send_message(
            f"✅ Komplain kamu (**#{cid}**) sudah diterima admin. "
            "Mohon ditunggu, kami akan segera menindaklanjuti.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Complaints(bot))
    print("Cog Complaints siap.")
