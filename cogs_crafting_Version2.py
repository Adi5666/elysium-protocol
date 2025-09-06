import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
from utils.db import db_ctx
from utils.embeds import make_crafting_embed
from utils.ui import CraftingView
from datetime import datetime

class Crafting(commands.Cog, name="Crafting"):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    @app_commands.command(name="craft_list", description="List available crafting recipes.")
    async def craft_list(self, interaction: discord.Interaction):
        with open("data/artifacts.json", "r", encoding="utf-8") as f:
            recipes = json.load(f)
        embed = make_crafting_embed(recipes)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="craft_start", description="Start crafting a recipe.")
    async def craft_start(self, interaction: discord.Interaction, recipe_id: int):
        async with db_ctx(self.bot.db) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM inventory WHERE player_id=? AND artifact_id IS NOT NULL",
                (interaction.user.id,)
            ) as cursor:
                count = (await cursor.fetchone())[0]
            if count >= self.config["crafting"]["queue_max_length"]:
                await interaction.response.send_message("Your crafting queue is full.", ephemeral=True)
                return
            await db.execute(
                "INSERT INTO inventory (player_id, artifact_id, obtained_at) VALUES (?, ?, ?)",
                (interaction.user.id, recipe_id, int(datetime.utcnow().timestamp()))
            )
            await db.commit()
        await interaction.response.send_message("Crafting started!", ephemeral=True)

    @app_commands.command(name="fusion_start", description="Start a fusion process for rare artifacts.")
    async def fusion_start(self, interaction: discord.Interaction, artifact_id1: int, artifact_id2: int):
        shiny_chance = self.config["crafting"]["fusion_shiny_chance"]
        proc_chance = self.config["crafting"]["artifact_proc_chance"]
        shiny = random.random() < shiny_chance
        proc = random.random() < proc_chance
        async with db_ctx(self.bot.db) as db:
            await db.execute("DELETE FROM inventory WHERE player_id=? AND artifact_id IN (?, ?)",
                             (interaction.user.id, artifact_id1, artifact_id2))
            fused_artifact_id = random.randint(100, 999)
            await db.execute(
                "INSERT INTO inventory (player_id, artifact_id, obtained_at) VALUES (?, ?, ?)",
                (interaction.user.id, fused_artifact_id, int(datetime.utcnow().timestamp()))
            )
            await db.commit()
        msg = "Fusion complete!"
        if shiny:
            msg += " ✨ You unlocked a shiny variant!"
        elif proc:
            msg += " 🌟 Rare artifact effect triggered!"
        await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Crafting(bot))