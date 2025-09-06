import aiosqlite
from contextlib import asynccontextmanager

DB_PATH = "elysium.db"

async def run_migrations(db_path=DB_PATH, migrations_file="migrations.sql"):
    async with aiosqlite.connect(db_path) as db:
        with open(migrations_file, "r", encoding="utf-8") as f:
            sql = f.read()
        await db.executescript(sql)
        await db.commit()

@asynccontextmanager
async def db_ctx(db):
    yield db

async def get_player_profile(db, discord_id):
    async with db.execute("SELECT * FROM players WHERE discord_id=?", (discord_id,)) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(zip([col[0] for col in cursor.description], row))

async def upsert_player_profile(db, discord_id, name, title=None, bio=None, accent_color=None, banner_url=None):
    async with db.execute("SELECT * FROM players WHERE discord_id=?", (discord_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        await db.execute(
            "INSERT INTO players (discord_id, name, profile_title, profile_bio, accent_color, banner_url) VALUES (?, ?, ?, ?, ?, ?)",
            (discord_id, name, title, bio, accent_color, banner_url)
        )
    else:
        await db.execute(
            "UPDATE players SET name=?, profile_title=?, profile_bio=?, accent_color=?, banner_url=? WHERE discord_id=?",
            (name, title, bio, accent_color, banner_url, discord_id)
        )
    await db.commit()

async def change_prefix(db, guild_id, new_prefix):
    async with db.execute("SELECT * FROM guilds WHERE id=?", (guild_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        await db.execute("INSERT INTO guilds (id, settings_json) VALUES (?, ?)", (guild_id, f'{{"prefix": "{new_prefix}"}}'))
    else:
        import json
        settings = json.loads(row[4] or "{}")
        settings["prefix"] = new_prefix
        await db.execute("UPDATE guilds SET settings_json=? WHERE id=?", (json.dumps(settings), guild_id))
    await db.commit()