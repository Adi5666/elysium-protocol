from discord.ext import commands
from discord import app_commands

def owner_only():
    def predicate(interaction):
        return interaction.user.id == interaction.client.owner_id
    return app_commands.check(predicate)

def claim_rate_limit():
    def decorator(func):
        async def wrapper(self, interaction, *args, **kwargs):
            if hasattr(interaction.user, "_last_claim") and (interaction.created_at - interaction.user._last_claim).total_seconds() < 5:
                await interaction.response.send_message("Rate limited: wait a few seconds before claiming again.", ephemeral=True)
                return
            interaction.user._last_claim = interaction.created_at
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator

def anti_snipe_check(user_id, spawn_row):
    if spawn_row and spawn_row[5] == user_id:
        return False
    return True