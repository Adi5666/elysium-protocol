import discord

class BattleView(discord.ui.View):
    def __init__(self, battle_id, pve=True):
        super().__init__(timeout=None)
        self.battle_id = battle_id
        self.pve = pve
        self.add_item(discord.ui.Button(label="Attack", custom_id=f"battle_{battle_id}_attack", style=discord.ButtonStyle.red))
        self.add_item(discord.ui.Button(label="Defend", custom_id=f"battle_{battle_id}_defend", style=discord.ButtonStyle.green))
        self.add_item(discord.ui.Button(label="Special", custom_id=f"battle_{battle_id}_special", style=discord.ButtonStyle.blurple))

class TradeView(discord.ui.View):
    def __init__(self, offers):
        super().__init__(timeout=None)
        for offer in offers:
            self.add_item(discord.ui.Button(
                label=f"Accept {offer['item_type']} #{offer['item_id']}",
                custom_id=f"trade_{offer['id']}_accept",
                style=discord.ButtonStyle.green
            ))

class CraftingView(discord.ui.View):
    def __init__(self, recipes):
        super().__init__(timeout=None)
        for recipe in recipes:
            self.add_item(discord.ui.Button(
                label=f"Craft {recipe['name']}",
                custom_id=f"craft_{recipe['id']}_start",
                style=discord.ButtonStyle.blurple
            ))

class PaginationView(discord.ui.View):
    def __init__(self, total_pages, current_page=1):
        super().__init__(timeout=None)
        self.total_pages = total_pages
        self.current_page = current_page
        self.add_item(discord.ui.Button(label="Previous", custom_id="page_prev", style=discord.ButtonStyle.secondary))
        self.add_item(discord.ui.Button(label=f"Page {current_page}/{total_pages}", disabled=True, style=discord.ButtonStyle.gray))
        self.add_item(discord.ui.Button(label="Next", custom_id="page_next", style=discord.ButtonStyle.secondary))