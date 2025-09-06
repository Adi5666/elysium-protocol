import discord
from discord.ext import commands
from discord import app_commands
import json
from utils.db import db_ctx
from utils.embeds import make_admin_embed
from utils.security import owner_only
from datetime import datetime

class Admin(commands.Cog, name="Admin"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="summon", description="(Owner only) Summon an NPC or artifact by ID.")
    @owner_only()
    async def summon(self, interaction: discord.Interaction, summon_type: str, template_id: int):
        async with db_ctx(self.bot.db) as db:
            if summon_type == "npc":
                await db.execute(
                    "INSERT INTO inventory (player_id, npc_id, obtained_at) VALUES (?, ?, ?)",
                    (interaction.user.id, template_id, int(datetime.utcnow().timestamp()))
                )
                await db.commit()
                await interaction.response.send_message(f"NPC {template_id} summoned to your inventory.", ephemeral=True)
            elif summon_type == "artifact":
                await db.execute(
                    "INSERT INTO inventory (player_id, artifact_id, obtained_at) VALUES (?, ?, ?)",
                    (interaction.user.id, template_id, int(datetime.utcnow().timestamp()))
                )
                await db.commit()
                await interaction.response.send_message(f"Artifact {template_id} summoned to your inventory.", ephemeral=True)
            else:
                await interaction.response.send_message("Invalid summon type.", ephemeral=True)

    @app_commands.command(name="setspawnchannel", description="Set spawn channel for this server.")
    @commands.has_permissions(administrator=True)
    async def setspawnchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        async with db_ctx(self.bot.db) as db:
            await db.execute(
                "UPDATE guilds SET settings_json = json_set(settings_json, '$.spawn_channel_id', ?) WHERE id=?",
                (channel.id, interaction.guild.id)
            )
            await db.commit()
        await interaction.response.send_message(f"Spawn channel set to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="backup_export", description="(Owner only) Export backup as JSON.")
    @owner_only()
    async def backup_export(self, interaction: discord.Interaction):
        async with db_ctx(self.bot.db) as db:
            tables = ["guilds", "players", "settlements", "buildings", "inventory", "artifacts", "active_spawns", "trades", "battles", "events", "logs"]
            backup = {}
            for t in tables:
                async with db.execute(f"SELECT * FROM {t}") as cursor:
                    backup[t] = [dict(zip([col[0] for col in cursor.description], row)) async for row in cursor]
            backup_json = json.dumps(backup, indent=2)
        await interaction.response.send_message(
            "Backup exported. (Check DM for full JSON)", ephemeral=True
        )
        await interaction.user.send(f"Here is your backup:\n```json\n{backup_json}\n```")

    @app_commands.command(name="import", description="(Owner only) Import backup from a JSON file.")
    @owner_only()
    async def import_backup(self, interaction: discord.Interaction, file: discord.Attachment):
        data = await file.read()
        try:
            backup = json.loads(data.decode())
        except Exception:
            await interaction.response.send_message("Invalid backup file.", ephemeral=True)
            return
        async with db_ctx(self.bot.db) as db:
            for t, rows in backup.items():
                await db.execute(f"DELETE FROM {t}")
                for row in rows:
                    keys = ", ".join(row.keys())
                    placeholders = ", ".join("?" for _ in row)
                    await db.execute(f"INSERT INTO {t} ({keys}) VALUES ({placeholders})", tuple(row.values()))
            await db.commit()
        await interaction.response.send_message("Backup imported successfully.", ephemeral=True)

    @app_commands.command(name="botmode", description="(Owner only) Toggle bot premium mode.")
    @owner_only()
    async def botmode(self, interaction: discord.Interaction, mode: str):
        value = True if mode.lower() == "on" else False
        async with db_ctx(self.bot.db) as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)", ("bot_premium_mode", str(value))
            )
            await db.commit()
        await interaction.response.send_message(f"Bot premium mode set to `{value}`.", ephemeral=True)

    @app_commands.command(name="logs", description="View audit logs (Owner only).")
    @owner_only()
    async def logs(self, interaction: discord.Interaction):
        async with db_ctx(self.bot.db) as db:
            async with db.execute(
                "SELECT * FROM logs ORDER BY created_at DESC LIMIT 20"
            ) as cursor:
                logs = [dict(zip([col[0] for col in cursor.description], row)) async for row in cursor]
        embed = make_admin_embed(logs)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="nuke_test_data", description="(Owner only) Nuke all test data with multiple confirmations.")
    @owner_only()
    async def nuke_test_data(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Type 'NUKE' to confirm data deletion.", ephemeral=True
        )
        def check(msg):
            return msg.author.id == interaction.user.id and msg.content == "NUKE"
        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Nuke cancelled (timeout).", ephemeral=True)
            return
        async with db_ctx(self.bot.db) as db:
            tables = ["guilds", "players", "settlements", "buildings", "inventory", "artifacts", "active_spawns", "trades", "battles", "events", "logs"]
            for t in tables:
                await db.execute(f"DELETE FROM {t}")
            await db.commit()
        await interaction.followup.send("Test data nuked.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))