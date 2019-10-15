from discord.ext import commands
import discord
from datetime import datetime, timedelta
from utils.leaderboard import leaderboard
import json
from utils.embeds import embedmanager
from utils.economy import economy
import utils.exceptions
import random
import sys


class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot._shop = {"perks": {}, "trophies": {}}
        self.load_shop()

    def load_shop(self):
        with open("shop.json") as f:
            shop = json.load(f)
        perks = shop["perks"]
        for i, perk in enumerate(perks["names"]):
            self.bot._shop["perks"][perk] = {'emote': perks["emotes"][i], 'price': perks["prices"][i],
                                             'description': perks["effects"][i]}
        perks = shop["collectibles"]
        for i, perk in enumerate(perks["names"]):
            self.bot._shop["trophies"][perk] = {'emote': perks["emotes"][i], 'price': perks["prices"][i],
                                                'description': None}

        self.bot._shop["trophies"]["navi"] = {'emote': "<a:linknavi:492377241548750858>"}

    @commands.group(name="shop", invoke_without_command=True)
    async def shop(self, ctx):
        await ctx.send("You entered the command incorrectly.", add_fields=[("Shop Options:",
                                                                            f"`{ctx.prefix}{ctx.command.name} perks`\n`{ctx.prefix}{ctx.command.name} trophies`\n`{ctx.prefix}{ctx.command.name} purchase`")])

    @shop.command(name='perks')
    async def equips(self, ctx):
        entries = self.bot._shop["perks"]
        string = ""
        currency_name = ctx.server_settings["EconomyCog"]["currency"]["value"]
        for name, entry in zip(entries, entries.values()):
            string += entry["emote"] + " " + name + " - " + str(entry["price"]) + " " + currency_name + entry[
                "description"].format(currency_name) + "\n"
        await ctx.send(string, add_footer=f"use {ctx.prefix}{ctx.command.parent.name} purchase [item name] to buy an item")

    @shop.command(name='trophies')
    async def collect(self, ctx):
        entries = self.bot._shop["trophies"]
        string = ""
        for name, entry in zip(entries, entries.values()):
            if name != "special" and name != "navi":
                string += entry["emote"] + " " + name + " - " + str(entry["price"]) + " " + \
                          ctx.server_settings["EconomyCog"]["currency"]["value"] + "\n"
        await ctx.send(string, add_footer=f"use {ctx.prefix}{ctx.command.parent.name} purchase [item name] to buy an item")

    @shop.command(name='purchase')
    async def purchase(self, ctx, item: str):
        item = item.title()
        item_type = 0
        if item in self.bot._shop["trophies"]:
            data = self.bot._shop["trophies"][item]
            redis_call = "trophies"
        elif item in self.bot._shop["perks"]:
            data = self.bot._shop["perks"][item]
            redis_call = "perks"
            item_type = 1
        else:
            await ctx.send("There is no item with that name.", image=False)
            return

        # exist = await self.bot.db.redis.smembers("member:{}:{}".format(ctx.message.author.id, redis_call))
        exist = await ctx.db.fetch("SELECT name FROM items WHERE guild_id = $1 AND member_id = $2", ctx.cluster_id,
                                   ctx.author.id)
        if exist:
            for it in exist:
                if it["name"] == item:
                    await ctx.send("You already own this item.", image=False)
                    return

        # Handle the economical shit
        currency = await economy.get_currency(ctx.db, ctx.message.author, ctx.cluster_id)
        currency_name = ctx.server_settings["EconomyCog"]["currency"]["value"]
        price = int(data["price"])

        if currency < price:
            await ctx.send("You don't have enough {}".format(currency_name), image=False)
            return
        await economy.update_currency(ctx.db, ctx.message.author, ctx.cluster_id, -price)

        # If purchase went correctly, assign the new item to the database
        await ctx.db.execute("INSERT INTO items (guild_id, member_id, name, type) VALUES ($1, $2, $3, $4)",
                             ctx.cluster_id, ctx.author.id, item, item_type)
        # await self.bot.db.redis.sadd("member:{}:{}".format(ctx.message.author.id, redis_call), item)

        await ctx.send(
            "You purchased `" + item + "` for `" + str(price) + "` " + currency_name + ".\nYour new balance is `" + str(
                currency - price) + "` " + currency_name + ".")


def setup(bot):
    bot.add_cog(ShopCog(bot))
