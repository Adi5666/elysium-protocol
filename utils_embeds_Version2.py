import discord

def make_profile_embed(profile, user):
    embed = discord.Embed(
        title=profile.get("profile_title") or f"{user.display_name}'s Profile",
        description=profile.get("profile_bio") or "No bio set.",
        color=int(profile.get("accent_color", "#3399FF").replace("#", ""), 16)
    )
    if profile.get("banner_url"):
        embed.set_image(url=profile["banner_url"])
    embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
    embed.add_field(name="Level", value=profile.get("level", 1))
    embed.add_field(name="Prestige", value=profile.get("prestige", 0))
    embed.set_footer(text="Elysium Protocol Profile")
    return embed

def make_help_embed(bot):
    embed = discord.Embed(
        title="Elysium Protocol Help",
        description="Get started, tips, and all commands.",
        color=0x3399FF
    )
    embed.add_field(
        name="Registration",
        value="`/register` - Create your profile\n`/profile` - View a profile\n`/profile_edit` - Edit profile details"
    )
    embed.add_field(
        name="Game",
        value="`/claim` - Claim spawns\n`/battle` - PvE/PvP combat\n`/trade` - Marketplace\n`/craft` - Fusion/crafting"
    )
    embed.add_field(
        name="Admin",
        value="`/setprefix` - Change bot prefix\n`/setspawnchannel` - Set spawn channel\n`/backup_export`/`backup_import` - Manage backups"
    )
    embed.add_field(
        name="Prefix",
        value="You can change the bot prefix using `/setprefix <new_prefix>` (Admins only)."
    )
    embed.add_field(
        name="Interactive Help",
        value="Type `/help` for this embed. For detailed help with commands, use `/help <command>`."
    )
    embed.set_footer(text=f"Prefix: {getattr(bot, 'prefix', '!')} • Elysium Protocol")
    return embed

def make_world_summary_embed(settlements, guild):
    embed = discord.Embed(
        title=f"{guild.name} World Summary",
        description="Settlements and their levels:",
        color=0x66CC66
    )
    for s in settlements:
        embed.add_field(name=s["name"], value=f"Level {s['level']}", inline=True)
    embed.set_footer(text="World tick summary")
    return embed

def make_spawn_embed(npcs, expires_at):
    embed = discord.Embed(
        title="A spawn has appeared!",
        description=f"Expires <t:{expires_at}:R>. Type `claim <slot>` to claim.",
        color=0xFFD700
    )
    for idx, npc in enumerate(npcs, 1):
        embed.add_field(name=f"Slot {idx}: {npc['name']}", value=f"Rarity: {npc['rarity']}", inline=False)
    embed.set_footer(text="Elysium Protocol Spawn")
    return embed

def make_battle_embed(logs, user):
    embed = discord.Embed(
        title="Recent Battles",
        description=f"For {user.display_name}",
        color=0xA259F7
    )
    for log in logs:
        embed.add_field(
            name=f"{log['type'].capitalize()} • {log['status']}",
            value=f"Started: <t:{log['started_at']}:R>\nLog: {log['log_json'][:128]}...",
            inline=False
        )
    embed.set_footer(text="Elysium Protocol Battles")
    return embed

def make_raid_phase_embed(npc):
    embed = discord.Embed(
        title=f"Raid Boss: {npc['name']}",
        description=npc.get("lore", ""),
        color=0xFF0000
    )
    embed.set_image(url=npc.get("image_url", ""))
    embed.add_field(name="Rarity", value=npc.get("rarity", "Unknown"), inline=True)
    embed.add_field(name="Role", value=npc.get("role", "Unknown"), inline=True)
    embed.set_footer(text="Raid phase started!")
    return embed

def make_trade_embed(offers, user):
    embed = discord.Embed(
        title="Marketplace Offers",
        description=f"For {user.display_name}",
        color=0x3399FF
    )
    for offer in offers:
        embed.add_field(
            name=f"{offer['item_type'].capitalize()} #{offer['item_id']}",
            value=f"Price: {offer['price']} • Status: {offer['status']}",
            inline=False
        )
    embed.set_footer(text="Elysium Protocol Marketplace")
    return embed

def make_crafting_embed(recipes):
    embed = discord.Embed(
        title="Crafting Recipes",
        color=0xFFD700
    )
    for recipe in recipes:
        embed.add_field(
            name=recipe["name"],
            value=f"Rarity: {recipe['rarity']}\nEffect: {recipe.get('effect', 'N/A')}",
            inline=False
        )
    embed.set_footer(text="Elysium Protocol Crafting")
    return embed

def make_premium_embed(status, user, guild):
    embed = discord.Embed(
        title="Premium Status",
        color=0xFF3860
    )
    for entry in status:
        who = user.mention if entry["kind"] == "user" else guild.name
        embed.add_field(
            name=f"{entry['kind'].capitalize()} Premium",
            value=f"For: {who}\nExpires: <t:{entry['expires_at']}:R>\nPerks: See `/help premium`",
            inline=False
        )
    embed.set_footer(text="Elysium Protocol Premium")
    return embed

def make_admin_embed(logs):
    embed = discord.Embed(
        title="Audit Logs",
        color=0xB0B0B0
    )
    for log in logs:
        embed.add_field(
            name=log["action"],
            value=f"User: {log['user_id']} • Time: <t:{log['created_at']}:R>\n{log['details']}",
            inline=False
        )
    embed.set_footer(text="Elysium Protocol Admin Logs")
    return embed