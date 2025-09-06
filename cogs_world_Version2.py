import discord
from discord.ext import commands, tasks
import asyncio
import json
from utils.db import db_ctx
from utils.embeds import make_world_summary_embed
from datetime import datetime

class World(commands.Cog, name="World"):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.world_tick_task.start()

    def cog_unload(self):
        self.world_tick_task.cancel()

    @tasks.loop(seconds=60)
    async def world_tick_task(self):
        await self.world_tick()

    async def world_tick(self):
        async with db_ctx(self.bot.db) as db:
            await self.simulate_settlements(db)
            await self.simulate_npcs(db)
            await self.backup_world(db)
            await self.send_world_summaries(db)

    async def simulate_settlements(self, db):
        async with db.execute("SELECT id, resources_json FROM settlements") as cursor:
            settlements = [dict(zip([column[0] for column in cursor.description], row)) async for row in cursor]
        for settlement in settlements:
            resources = json.loads(settlement["resources_json"] or "{}")
            resources["food"] = resources.get("food", 0) + 5
            resources["wood"] = resources.get("wood", 0) + 2
            resources["stone"] = resources.get("stone", 0) + 1
            await db.execute(
                "UPDATE settlements SET resources_json=? WHERE id=?",
                (json.dumps(resources), settlement["id"])
            )
        await db.commit()

    async def simulate_npcs(self, db):
        async with db.execute("SELECT * FROM world_npcs WHERE status='active'") as cursor:
            npcs = [dict(zip([column[0] for column in cursor.description], row)) async for row in cursor]
        for npc in npcs:
            if random.random() < 0.03:
                await db.execute(
                    "UPDATE world_npcs SET job=?, migrated_at=? WHERE id=?",
                    ("scout" if npc["job"] != "scout" else "worker", int(datetime.utcnow().timestamp()), npc["id"])
                )
            if random.random() < 0.005 and not npc["converted_to_collectible"]:
                await db.execute(
                    "UPDATE world_npcs SET converted_to_collectible=1 WHERE id=?",
                    (npc["id"],)
                )
        await db.commit()

    async def backup_world(self, db):
        pass

    async def send_world_summaries(self, db):
        for guild in self.bot.guilds:
            chan_id = self.config.get("default_announce_channel") or getattr(guild, "system_channel", None)
            channel = guild.get_channel(chan_id) if chan_id else guild.system_channel
            if not channel:
                continue
            async with db.execute("SELECT name, level FROM settlements WHERE guild_id=?", (guild.id,)) as cursor:
                settlements = [dict(zip([column[0] for column in cursor.description], row)) async for row in cursor]
            if settlements:
                embed = make_world_summary_embed(settlements, guild)
                await channel.send(embed=embed)

    @commands.command(name="world_summary")
    async def world_summary(self, ctx):
        async with db_ctx(self.bot.db) as db:
            async with db.execute("SELECT name, level FROM settlements WHERE guild_id=?", (ctx.guild.id,)) as cursor:
                settlements = [dict(zip([column[0] for column in cursor.description], row)) async for row in cursor]
            if not settlements:
                await ctx.send("No settlements found.")
                return
            embed = make_world_summary_embed(settlements, ctx.guild)
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(World(bot))