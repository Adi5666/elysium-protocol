import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from utils.db import db_ctx
from utils.embeds import make_premium_embed
from datetime import datetime, timedelta

class Premium(commands.Cog, name="Premium"):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.expiry_scheduler.start()

    def cog_unload(self):
        self.expiry_scheduler.cancel()

    @tasks.loop(minutes=60)
    async def expiry_scheduler(self):
        await self.check_expiry()

    async def check_expiry(self):
        now = int(datetime.utcnow().timestamp())
        async with db_ctx(self.bot.db) as db:
            async with db.execute("SELECT * FROM premium WHERE expires_at IS NOT NULL") as cursor:
                premiums = [dict(zip([col[0] for col in cursor.description], row)) async for row in cursor]
            for entry in premiums:
                expires_in = entry["expires_at"] - now
                user_id = entry["user_id"]
                guild_id = entry["guild_id"]
                kind = entry["kind"]
                if expires_in <= 7*24*3600 and not entry["notified_7d"]:
                    await self.send_reminder(user_id, guild_id, kind, 7)
                    await db.execute("UPDATE premium SET notified_7d=1 WHERE id=?", (entry["id"],))
                if expires_in <= 48*3600 and not entry["notified_48h"]:
                    await self.send_reminder(user_id, guild_id, kind, 2)
                    await db.execute("UPDATE premium SET notified_48h=1 WHERE id=?", (entry["id"],))
                if expires_in <= 0:
                    await self.revoke_premium(user_id, guild_id, kind)
                    await db.execute("DELETE FROM premium WHERE id=?", (entry["id"],))
            await db.commit()

    async def send_reminder(self, user_id, guild_id, kind, days):
        user = self.bot.get_user(user_id) if user_id else None
        guild = self.bot.get_guild(guild_id) if guild_id else None
        target = user or (guild.owner if guild else None)
        if target:
            await target.send(
                f"⏰ Your Elysium Protocol premium ({kind}) expires in {days} days! Renew soon to keep your perks."
            )

    async def revoke_premium(self, user_id, guild_id, kind):
        user = self.bot.get_user(user_id) if user_id else None
        guild = self.bot.get_guild(guild_id) if guild_id else None
        target = user or (guild.owner if guild else None)
        if target:
            await target.send(
                f"❗ Your Elysium Protocol premium ({kind}) has expired. Perks have been revoked."
            )
        if guild:
            channel = guild.system_channel
            if channel:
                await channel.send("🔔 Premium perks have expired for this server.")

    @app_commands.command(name="premium_grant_user", description="Grant premium to a user for a duration.")
    async def premium_grant_user(self, interaction: discord.Interaction, user: discord.User, duration_days: int, reason: str = ""):
        expires_at = int((datetime.utcnow() + timedelta(days=duration_days)).timestamp())
        async with db_ctx(self.bot.db) as db:
            await db.execute(
                "INSERT INTO premium (kind, user_id, expires_at, granted_by, reason) VALUES (?, ?, ?, ?, ?)",
                ("user", user.id, expires_at, interaction.user.id, reason)
            )
            await db.commit()
        await user.send(f"🎉 You have been granted premium for {duration_days} days!\nReason: {reason}")
        await interaction.response.send_message(f"Premium granted to {user.mention}.", ephemeral=True)

    @app_commands.command(name="premium_grant_server", description="Grant premium to a server for a duration.")
    async def premium_grant_server(self, interaction: discord.Interaction, duration_days: int):
        expires_at = int((datetime.utcnow() + timedelta(days=duration_days)).timestamp())
        async with db_ctx(self.bot.db) as db:
            await db.execute(
                "INSERT INTO premium (kind, guild_id, expires_at, granted_by) VALUES (?, ?, ?, ?)",
                ("server", interaction.guild.id, expires_at, interaction.user.id)
            )
            await db.commit()
        owner = interaction.guild.owner
        if owner:
            await owner.send(f"🎉 Your server has been granted premium for {duration_days} days!")
        await interaction.response.send_message("Server premium granted.", ephemeral=True)

    @app_commands.command(name="premium_revoke_user", description="Revoke premium from a user.")
    async def premium_revoke_user(self, interaction: discord.Interaction, user: discord.User):
        async with db_ctx(self.bot.db) as db:
            await db.execute("DELETE FROM premium WHERE kind='user' AND user_id=?", (user.id,))
            await db.commit()
        await user.send("❌ Your premium has been revoked.")
        await interaction.response.send_message(f"Premium revoked from {user.mention}.", ephemeral=True)

    @app_commands.command(name="premium_revoke_server", description="Revoke premium from this server.")
    async def premium_revoke_server(self, interaction: discord.Interaction):
        async with db_ctx(self.bot.db) as db:
            await db.execute("DELETE FROM premium WHERE kind='server' AND guild_id=?", (interaction.guild.id,))
            await db.commit()
        owner = interaction.guild.owner
        if owner:
            await owner.send("❌ Your server's premium has been revoked.")
        await interaction.response.send_message("Server premium revoked.", ephemeral=True)

    @app_commands.command(name="premium_info", description="Show premium status and perks.")
    async def premium_info(self, interaction: discord.Interaction):
        async with db_ctx(self.bot.db) as db:
            async with db.execute(
                "SELECT * FROM premium WHERE user_id=? OR guild_id=?",
                (interaction.user.id, interaction.guild.id)
            ) as cursor:
                status = [dict(zip([col[0] for col in cursor.description], row)) async for row in cursor]
        embed = make_premium_embed(status, interaction.user, interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Premium(bot))