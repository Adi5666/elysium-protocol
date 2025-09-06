import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
import json
from utils.db import db_ctx
from utils.embeds import make_spawn_embed
from utils.security import claim_rate_limit, anti_snipe_check
from datetime import datetime

class Spawn(commands.Cog, name="Spawn"):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.spawn_task.start()

    def cog_unload(self):
        self.spawn_task.cancel()

    @tasks.loop(seconds=30)
    async def spawn_task(self):
        for guild in self.bot.guilds:
            try:
                await self.try_spawn(guild)
            except Exception as e:
                print(f"Spawn error in guild {guild.id}: {e}")

    async def try_spawn(self, guild):
        async with db_ctx(self.bot.db) as db:
            chan_id = self.config.get("default_announce_channel") or getattr(guild, "system_channel", None)
            channel = guild.get_channel(chan_id) if chan_id else guild.system_channel
            if not channel:
                return
            rate = self.config["spawn_rates"]["base"]
            if random.random() > rate:
                return
            npc_templates = await self.get_random_npcs(db)
            expires_at = int(datetime.utcnow().timestamp()) + 60
            npc_ids = [npc["id"] for npc in npc_templates]
            await db.execute(
                "INSERT INTO active_spawns (guild_id, channel_id, npc_ids, spawn_type, expires_at) VALUES (?, ?, ?, ?, ?)",
                (guild.id, channel.id, json.dumps(npc_ids), "spawn", expires_at)
            )
            await db.commit()
            embed = make_spawn_embed(npc_templates, expires_at)
            await channel.send(embed=embed)

    async def get_random_npcs(self, db):
        weights = self.config["rarity_weights"]
        async with db.execute("SELECT * FROM npcs") as cursor:
            npcs = [dict(zip([column[0] for column in cursor.description], row)) async for row in cursor]
        population = [npc for npc in npcs if npc["category"] == "spawn"]
        choices = random.choices(
            population,
            weights=[weights.get(npc["rarity"], 1) for npc in population],
            k=random.randint(1, 3)
        )
        return choices

    @app_commands.command(name="claim", description="Type to claim a spawn slot (fairness enforced).")
    @claim_rate_limit()
    async def claim(self, interaction: discord.Interaction, slot: int):
        user = interaction.user
        async with db_ctx(self.bot.db) as db:
            async with db.execute(
                "SELECT * FROM active_spawns WHERE channel_id=? AND expires_at > strftime('%s','now') AND claimed_by IS NULL",
                (interaction.channel.id,)
            ) as cursor:
                spawn_row = await cursor.fetchone()
            if not spawn_row:
                await interaction.response.send_message("No active spawn to claim.", ephemeral=True)
                return
            if not anti_snipe_check(user.id, spawn_row):
                await interaction.response.send_message("Claim failed: fairness rule triggered.", ephemeral=True)
                return
            await db.execute(
                "UPDATE active_spawns SET claimed_by=?, claim_slot=?, claim_time=? WHERE id=?",
                (user.id, slot, int(datetime.utcnow().timestamp()), spawn_row[0])
            )
            await db.commit()
            await interaction.response.send_message(
                f"{user.mention} claimed slot {slot}!", ephemeral=False
            )

    @app_commands.command(name="spawn_setchannel", description="Set the spawn channel for this server.")
    @commands.has_permissions(administrator=True)
    async def spawn_setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        async with db_ctx(self.bot.db) as db:
            await db.execute(
                "UPDATE guilds SET settings_json = json_set(settings_json, '$.spawn_channel_id', ?) WHERE id=?",
                (channel.id, interaction.guild.id)
            )
            await db.commit()
        await interaction.response.send_message(
            f"Spawn channel set to {channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="spawn_info", description="Show current spawn info and rules.")
    async def spawn_info(self, interaction: discord.Interaction):
        info = (
            "**Spawn System:**\n"
            "- Spawns appear in configured channel.\n"
            "- Claim by typing: `claim <slot>`.\n"
            "- Fairness, rate limits, and anti-abuse are enforced.\n"
            "- Premium servers get more frequent/rare spawns.\n"
        )
        await interaction.response.send_message(info, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Spawn(bot))
