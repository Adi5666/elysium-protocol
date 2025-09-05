-- Elysium Protocol DB Schema & Migrations

PRAGMA journal_mode = WAL;

-- Guilds table
CREATE TABLE IF NOT EXISTS guilds (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id INTEGER,
    premium_expires_at INTEGER,
    banner_url TEXT,
    faction_banner_url TEXT,
    settings_json TEXT DEFAULT '{}'
);

-- Players (Users) table
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    discord_id INTEGER NOT NULL UNIQUE,
    name TEXT,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    prestige INTEGER DEFAULT 0,
    faction TEXT,
    shiny_unlocked INTEGER DEFAULT 0,
    shiny_variant_tag TEXT,
    premium_expires_at INTEGER,
    profile_title TEXT,
    profile_bio TEXT,
    accent_color TEXT DEFAULT '#3399FF',
    frame TEXT,
    banner_url TEXT,
    weekly_summary_opt_in INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

-- Premium table (tracks all premium grants)
CREATE TABLE IF NOT EXISTS premium (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL, -- 'user', 'server', 'bot'
    user_id INTEGER,
    guild_id INTEGER,
    expires_at INTEGER,
    granted_by INTEGER,
    reason TEXT,
    notified_7d INTEGER DEFAULT 0,
    notified_48h INTEGER DEFAULT 0
);

-- NPC templates (master data)
CREATE TABLE IF NOT EXISTS npcs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    rarity TEXT NOT NULL,
    category TEXT NOT NULL,
    role TEXT NOT NULL,
    stats_json TEXT NOT NULL,
    abilities_json TEXT NOT NULL,
    lore TEXT,
    image_url TEXT,
    shiny_asset_tag TEXT
);

-- Active Spawns
CREATE TABLE IF NOT EXISTS active_spawns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    npc_ids TEXT NOT NULL, -- JSON array of NPC template IDs
    spawn_type TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s','now')),
    expires_at INTEGER,
    claimed_by INTEGER,
    claim_slot INTEGER, -- 1/2/3
    claim_time INTEGER
);

-- World settlements
CREATE TABLE IF NOT EXISTS settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    owner_id INTEGER,
    name TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s','now')),
    level INTEGER DEFAULT 1,
    faction TEXT,
    banner_url TEXT,
    resources_json TEXT DEFAULT '{}'
);

-- Buildings (within settlements)
CREATE TABLE IF NOT EXISTS buildings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    settlement_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    status TEXT,
    started_at INTEGER,
    finished_at INTEGER
);

-- Living World NPCs (assigned to settlements)
CREATE TABLE IF NOT EXISTS world_npcs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_template_id INTEGER NOT NULL,
    settlement_id INTEGER NOT NULL,
    role TEXT,
    job TEXT,
    status TEXT,
    migrated_at INTEGER,
    converted_to_collectible INTEGER DEFAULT 0
);

-- Artifacts (collectible & loot)
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    owner_id INTEGER,
    obtained_at INTEGER DEFAULT (strftime('%s','now')),
    shiny_variant_tag TEXT,
    equipped INTEGER DEFAULT 0
);

-- Inventory (player collectibles)
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    npc_id INTEGER,
    artifact_id INTEGER,
    obtained_at INTEGER DEFAULT (strftime('%s','now'))
);

-- Trades (marketplace offers)
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER NOT NULL,
    buyer_id INTEGER,
    item_type TEXT NOT NULL, -- npc, artifact, resource
    item_id INTEGER NOT NULL,
    price INTEGER NOT NULL,
    status TEXT DEFAULT 'open',
    created_at INTEGER DEFAULT (strftime('%s','now')),
    accepted_at INTEGER,
    declined_at INTEGER
);

-- Battles (PvE & PvP)
CREATE TABLE IF NOT EXISTS battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    type TEXT NOT NULL, -- pve, pvp, raid
    challenger_id INTEGER,
    opponent_id INTEGER,
    status TEXT,
    started_at INTEGER,
    finished_at INTEGER,
    log_json TEXT
);

-- Events (quests, anomalies, world events)
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    event_type TEXT,
    npc_id INTEGER,
    started_at INTEGER DEFAULT (strftime('%s','now')),
    expires_at INTEGER,
    status TEXT,
    data_json TEXT
);

-- Logs (for moderation and audit)
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    action TEXT,
    details TEXT,
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

-- Settings (misc global bot settings)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- DB version for migrations
CREATE TABLE IF NOT EXISTS db_version (
    version INTEGER PRIMARY KEY
);

-- Artifacts master data
CREATE TABLE IF NOT EXISTS artifact_templates (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    rarity TEXT NOT NULL,
    effect TEXT,
    lore TEXT,
    image_url TEXT,
    shiny_asset_tag TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_players_discord_id ON players(discord_id);
CREATE INDEX IF NOT EXISTS idx_active_spawns_guild_id ON active_spawns(guild_id);
CREATE INDEX IF NOT EXISTS idx_inventory_player_id ON inventory(player_id);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_battles_status ON battles(status);

-- Future migrations: add here with new DB version and ALTERs
