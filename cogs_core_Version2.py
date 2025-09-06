import discord
from discord.ext import commands
from discord import app_commands
from utils.db import db_ctx, get_player_profile, upsert_player_profile
from utils.embeds import make_profile_embed, make_help_embed

class Core(commands.Cog, name="Core"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="register", description="Register your player profile.")
    async def register(self, interaction: discord.Interaction):
        user = interaction.user
        async with db_ctx(self.bot.db) as db:
            profile = await get_player_profile(db, user.id)
            if profile:
                await interaction.response.send_message("Already registered.", ephemeral=True)
                return
            await upsert_player_profile(db, user.id, user.display_name)
        await interaction.response.send_message("Registration successful!", ephemeral=True)

    @app_commands.command(name="profile", description="View a player's profile.")
    async def profile(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        async with db_ctx(self.bot.db) as db:
            profile = await get_player_profile(db, user.id)
        if not profile:
            await interaction.response.send_message("Profile not found.", ephemeral=True)
            return
        embed = make_profile_embed(profile, user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="profile_edit", description="Edit your profile details.")
    async def profile_edit(self, interaction: discord.Interaction, title: str = None, bio: str = None, accent_color: str = None, banner_url: str = None):
        user = interaction.user
        async with db_ctx(self.bot.db) as db:
            await upsert_player_profile(db, user.id, user.display_name, title, bio, accent_color, banner_url)
        await interaction.response.send_message("Profile updated.", ephemeral=True)

    @app_commands.command(name="help", description="Show interactive help.")
    async def help(self, interaction: discord.Interaction):
        embed = make_help_embed(self.bot)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Core(bot))