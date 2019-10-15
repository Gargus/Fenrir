import asyncio
import discord
from discord.ext import commands

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def on_ready(self):
        pass

    # Run redis related things here
    async def main_setup(self):
        #self.bot.loop.create_task(self.update_stats())
        await self.update_stats()

    async def update_stats(self):
        while True:
            member_count = self.get_member_count()
            guild_count = self.get_guild_count()
            await self.bot.db.redis.set("bot:member_count", member_count)
            await self.bot.db.redis.set("bot:guild_count", guild_count)
            await self.bot.change_presence(status=discord.Status.online,
                                           activity=discord.Game(f"with {guild_count} Realms"))
            await asyncio.sleep(1800)


    def get_member_count(self):
        number = 0
        for member in self.bot.get_all_members():
            number += 1
        return number

    def get_guild_count(self):
        return len(self.bot.guilds)


def setup(bot):
    bot.add_cog(StatsCog(bot))
