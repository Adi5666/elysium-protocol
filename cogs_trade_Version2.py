import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils.db import db_ctx
from utils.embeds import make_trade_embed
from utils.ui import TradeView
from datetime import datetime

class Trade(commands.Cog, name="Trade"):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    @app_commands.command(name="trade_offer_create", description="Create a trade offer in the marketplace.")
    async def trade_offer_create(self, interaction: discord.Interaction, item_type: str, item_id: int, price: int):
        async with db_ctx(self.bot.db) as db:
            await db.execute(
                "INSERT INTO trades (seller_id, item_type, item_id, price, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (interaction.user.id, item_type, item_id, price, "open", int(datetime.utcnow().timestamp()))
            )
            await db.commit()
        await interaction.response.send_message("Trade offer created!", ephemeral=True)

    @app_commands.command(name="trade_list", description="List your open trade offers.")
    async def trade_list(self, interaction: discord.Interaction):
        async with db_ctx(self.bot.db) as db:
            async with db.execute(
                "SELECT * FROM trades WHERE seller_id=? AND status='open' ORDER BY created_at DESC LIMIT ?",
                (interaction.user.id, self.config["trade"]["pagination_size"])
            ) as cursor:
                offers = [dict(zip([col[0] for col in cursor.description], row)) async for row in cursor]
        if not offers:
            await interaction.response.send_message("No open trade offers.", ephemeral=True)
            return
        embed = make_trade_embed(offers, interaction.user)
        await interaction.response.send_message(embed=embed, view=TradeView(offers), ephemeral=True)

    @app_commands.command(name="trade_accept", description="Accept a trade offer.")
    async def trade_accept(self, interaction: discord.Interaction, trade_id: int):
        async with db_ctx(self.bot.db) as db:
            async with db.execute("SELECT * FROM trades WHERE id=? AND status='open'", (trade_id,)) as cursor:
                trade = await cursor.fetchone()
            if not trade:
                await interaction.response.send_message("Trade not found or already closed.", ephemeral=True)
                return
            await db.execute(
                "UPDATE trades SET status='accepted', buyer_id=?, accepted_at=? WHERE id=?",
                (interaction.user.id, int(datetime.utcnow().timestamp()), trade_id)
            )
            await db.commit()
        await interaction.response.send_message("Trade accepted!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Trade(bot))