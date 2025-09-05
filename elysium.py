import os
import sys
import asyncio
import logging
import json
from discord.ext import commands, tasks
import discord
import aiosqlite

# --- CONFIG LOADING ---

CONFIG_PATH = "config.json"
MIGRATIONS_PATH = "migrations.sql"
DB_PATH = "elysium.db"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="[{asctime}] [{levelname}] {name}: {message}",
    style="{"
)
logger = logging.getLogger("elysium")

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True
intents.dm_messages = True
intents.presences = False
intents.reactions = True

# --- MIGRATION RUNNER ---

async def run_migrations(db: aiosqlite.Connection):
    # Read migrations.sql and apply if needed
    with open(MIGRATIONS_PATH, "r", encoding="utf-8") as f:
        sql = f.read()
    await db.executescript(sql)
    await db.commit()
    logger.info("DB migrations applied.")

# --- BOT DEFINITION ---

class ElysiumBot(commands.Bot):
    def __init__(self, config):
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.get("default_prefix", "!")),
            intents=intents,
            help_command=None
        )
        self.config = config
        self.db = None
        self._ready = asyncio.Event()
        self.bg_tasks = []

    async def setup_hook(self):
        # DB connect and run migrations
        self.db = await aiosqlite.connect(DB_PATH, isolation_level=None)
        await run_migrations(self.db)
        # Load cogs
        await self.load_all_cogs()
        # Start background tasks
        self.bg_tasks.append(self.loop.create_task(self.world_tick_task()))
        self.bg_tasks.append(self.loop.create_task(self.premium_expiry_task()))
        self.bg_tasks.append(self.loop.create_task(self.spawn_cleanup_task()))
        self._ready.set()
        logger.info("Elysium bot setup complete.")

    async def load_all_cogs(self):
        await self.load_extension("cogs.core")
        await self.load_extension("cogs.spawn")
        await self.load_extension("cogs.world")
        await self.load_extension("cogs.battle")
        await self.load_extension("cogs.trade")
        await self.load_extension("cogs.crafting")
        await self.load_extension("cogs.premium")
        await self.load_extension("cogs.admin")
        logger.info("All cogs loaded.")

    async def close(self):
        for task in self.bg_tasks:
            task.cancel()
        if self.db:
            await self.db.close()
        await super().close()
        logger.info("Bot shutdown complete.")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} ({self.user.id})")

    async def on_guild_join(self, guild):
        await self.send_guild_owner_dm(guild)

    async def send_guild_owner_dm(self, guild):
        owner = guild.owner
        if owner is None:
            return
        try:
            setup_msg = (
                f"👋 Welcome to Elysium Protocol!\n\n"
                f"To get started, set a spawn channel with `/spawn setchannel`.\n"
                f"Check `/help` for all commands.\n"
                f"Premium boost available for servers and users: try `/premium info`.\n"
                f"Backups, world simulation, and claims are all managed server-side.\n"
                f"Need support? Ping the bot owner or see README."
            )
            await owner.send(setup_msg)
            logger.info(f"Sent setup DM to server owner {owner} in guild {guild.name}")
        except Exception as e:
            logger.warning(f"Failed to DM server owner {owner} in guild {guild.name}: {e}")

    async def premium_expiry_task(self):
        # Periodically (every hour) check for soon-to-expire and expired premium entries
        while not self.is_closed():
            try:
                await self._ready.wait()
                await self.handle_premium_expiry()
            except Exception as e:
                logger.error(f"Premium expiry task error: {e}")
            await asyncio.sleep(3600)

    async def handle_premium_expiry(self):
        # 7d and 48h pre-expiry reminders, expiry notifications
        async with self.db.execute(
            "SELECT id, kind, user_id, guild_id, expires_at, notified_7d, notified_48h FROM premium WHERE expires_at IS NOT NULL"
        ) as cursor:
            rows = await cursor.fetchall()
        now = int(asyncio.get_event_loop().time())
        for row in rows:
            id, kind, user_id, guild_id, expires_at, notified_7d, notified_48h = row
            if expires_at - now <= 7*24*3600 and not notified_7d:
                await self.send_premium_reminder(kind, user_id, guild_id, expires_at, days=7)
                await self.db.execute("UPDATE premium SET notified_7d=1 WHERE id=?", (id,))
            if expires_at - now <= 48*3600 and not notified_48h:
                await self.send_premium_reminder(kind, user_id, guild_id, expires_at, days=2)
                await self.db.execute("UPDATE premium SET notified_48h=1 WHERE id=?", (id,))
            if expires_at <= now:
                await self.handle_premium_expiry_event(kind, user_id, guild_id)
                await self.db.execute("DELETE FROM premium WHERE id=?", (id,))
        await self.db.commit()

    async def send_premium_reminder(self, kind, user_id, guild_id, expires_at, days):
        # DM user/server owner
        user = self.get_user(user_id) if user_id else None
        guild = self.get_guild(guild_id) if guild_id else None
        target = user or (guild.owner if guild else None)
        if not target:
            return
        try:
            await target.send(
                f"⏰ Your Elysium Protocol premium ({kind}) expires in {days} days! "
                f"Renew soon to keep your perks."
            )
            logger.info(f"Sent {days}d premium expiry reminder to {target}")
        except Exception as e:
            logger.warning(f"Failed to DM premium reminder to {target}: {e}")

    async def handle_premium_expiry_event(self, kind, user_id, guild_id):
        # DM user/server owner, announce in guild if needed
        user = self.get_user(user_id) if user_id else None
        guild = self.get_guild(guild_id) if guild_id else None
        target = user or (guild.owner if guild else None)
        if target:
            try:
                await target.send(
                    f"❗ Your Elysium Protocol premium ({kind}) has expired. Perks have been revoked."
                )
            except Exception as e:
                logger.warning(f"Failed to DM premium expiry to {target}: {e}")
        if guild:
            # Announce in server (if server-premium)
            try:
                chan_id = config.get("default_announce_channel")
                channel = guild.get_channel(chan_id) if chan_id else guild.system_channel
                if channel:
                    await channel.send(
                        f"🔔 Premium perks have expired for this server."
                    )
            except Exception as e:
                logger.warning(f"Failed to announce premium expiry in guild {guild}: {e}")

    async def world_tick_task(self):
        # Run world tick every config["tick_interval"]
        interval = config.get("tick_interval", 60)
        while not self.is_closed():
            try:
                await self._ready.wait()
                await self.run_world_tick()
            except Exception as e:
                logger.error(f"World tick error: {e}")
            await asyncio.sleep(interval)

    async def run_world_tick(self):
        # Call the world tick logic in /cogs/world.py
        cog = self.get_cog("World")
        if cog:
            await cog.world_tick()
        else:
            logger.warning("World cog not loaded for tick.")

    async def spawn_cleanup_task(self):
        # Clean up expired spawns
        interval = config.get("spawn_cleanup_interval", 120)
        while not self.is_closed():
            try:
                await self._ready.wait()
                await self.cleanup_expired_spawns()
            except Exception as e:
                logger.error(f"Spawn cleanup error: {e}")
            await asyncio.sleep(interval)

    async def cleanup_expired_spawns(self):
        async with self.db.execute(
            "DELETE FROM active_spawns WHERE expires_at IS NOT NULL AND expires_at < strftime('%s','now')"
        ):
            pass
        await self.db.commit()
        logger.info("Expired spawns cleaned up.")

# --- MAIN ---

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN environment variable not set.")
        sys.exit(1)
    bot = ElysiumBot(config)
    try:
        bot.run(token)
    except KeyboardInterrupt:
        print("Bot stopped by user.")

if __name__ == "__main__":
    main()
