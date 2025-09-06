import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from utils.db import db_ctx
from utils.embeds import make_battle_embed, make_raid_phase_embed
from utils.ui import BattleView
from datetime import datetime

class Battle(commands.Cog, name="Battle"):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    @app_commands.command(name="pve_raid_start", description="Start a PvE raid against a boss NPC.")
    async def pve_raid_start(self, interaction: discord.Interaction):
        async with db_ctx(self.bot.db) as db:
            async with db.execute("SELECT * FROM npcs WHERE category='raid' OR category='boss' ORDER BY RANDOM() LIMIT 1") as cursor:
                npc = await cursor.fetchone()
            if not npc:
                await interaction.response.send_message("No raid bosses available.", ephemeral=True)
                return
            battle_id = await self.create_battle(db, interaction.guild.id, "pve", interaction.user.id, npc_id=npc[0])
        await interaction.response.send_message(
            "Raid started! Prepare for battle...",
            embed=make_raid_phase_embed(npc),
            view=BattleView(battle_id, pve=True),
            ephemeral=False
        )

    @app_commands.command(name="pvp_challenge", description="Challenge another user to PvP battle.")
    async def pvp_challenge(self, interaction: discord.Interaction, user: discord.User):
        if user.id == interaction.user.id:
            await interaction.response.send_message("You cannot challenge yourself.", ephemeral=True)
            return
        async with db_ctx(self.bot.db) as db:
            battle_id = await self.create_battle(db, interaction.guild.id, "pvp", interaction.user.id, opponent_id=user.id)
        await interaction.response.send_message(
            f"{interaction.user.mention} challenged {user.mention}!",
            view=BattleView(battle_id, pve=False),
            ephemeral=False
        )

    async def create_battle(self, db, guild_id, btype, challenger_id, opponent_id=None, npc_id=None):
        started_at = int(datetime.utcnow().timestamp())
        await db.execute(
            "INSERT INTO battles (guild_id, type, challenger_id, opponent_id, status, started_at, log_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                guild_id,
                btype,
                challenger_id,
                opponent_id if opponent_id else npc_id,
                "active",
                started_at,
                "[]"
            )
        )
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cursor:
            row = await cursor.fetchone()
        return row[0]

    @app_commands.command(name="battle_log", description="View your recent battle logs.")
    async def battle_log(self, interaction: discord.Interaction):
        async with db_ctx(self.bot.db) as db:
            async with db.execute(
                "SELECT id, type, status, started_at, finished_at, log_json FROM battles WHERE challenger_id=? OR opponent_id=? ORDER BY started_at DESC LIMIT 6",
                (interaction.user.id, interaction.user.id)
            ) as cursor:
                logs = [dict(zip([col[0] for col in cursor.description], row)) async for row in cursor]
        if not logs:
            await interaction.response.send_message("No recent battles found.", ephemeral=True)
            return
        embed = make_battle_embed(logs, interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_button_click(self, interaction: discord.Interaction):
        if not interaction.data or not interaction.data.get("custom_id", "").startswith("battle_"):
            return
        parts = interaction.data["custom_id"].split("_")
        if len(parts) < 3:
            return
        battle_id = int(parts[1])
        action = parts[2]
        async with db_ctx(self.bot.db) as db:
            async with db.execute("SELECT * FROM battles WHERE id=?", (battle_id,)) as cursor:
                battle = await cursor.fetchone()
            if not battle or battle[5] != "active":
                await interaction.response.send_message("Battle is not active.", ephemeral=True)
                return
            random.seed(battle_id + int(datetime.utcnow().timestamp()))
            result, log = await self.perform_battle_action(db, battle, interaction.user.id, action)
            await db.execute(
                "UPDATE battles SET log_json=json_insert(log_json, '$[#]', ?) WHERE id=?",
                (log, battle_id)
            )
            if result == "win":
                await db.execute("UPDATE battles SET status='finished', finished_at=? WHERE id=?",
                                 (int(datetime.utcnow().timestamp()), battle_id))
            await db.commit()
            await interaction.response.send_message(log, ephemeral=False)

    async def perform_battle_action(self, db, battle, user_id, action):
        if random.random() < 0.5:
            return "win", f"{user_id} performed {action} and won the round!"
        else:
            return "continue", f"{user_id} performed {action}. The battle continues..."

async def setup(bot):
    await bot.add_cog(Battle(bot))