import dbl
import discord
from discord.ext import commands
from urllib.parse import urlencode
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from utils.economy import economy
import config

class PublicCog(commands.Cog):
    """Handles interactions with the discordbots.org API"""
    
    def __init__(self, bot):
        self.bot = bot
        self.token = config.token
        # set this to your DBL token
        self.dblpy = dbl.DBLClient(self.bot, self.token)
        self.bot.loop.create_task(self.update_stats())

    async def update_stats(self):
        """This function runs every 30 minutes to automatically update your server count"""

        """Add this line here so it won't attempt to post before the dbl client is properly set up"""
        await self.bot.wait_until_ready()

        while True:
            logger.info('attempting to post server count')
            try:
                await self.dblpy.post_guild_count()
                logger.info('posted server count ({})'.format(len(self.bot.guilds)))
            except Exception as e:
                logger.exception('Failed to post server count\n{}: {}'.format(type(e).__name__, e))
            await asyncio.sleep(1800)

    @commands.command(name="claim")
    async def claim(self, ctx):

        voter = await ctx.db.fetch("SELECT date, claimed FROM voters WHERE user_id = $1 AND bot_id = $2 AND type = $3",
                                   ctx.author.id, 578372226252931072, "upvote")
        if not voter:
            await ctx.send("You've not voted yet! Go to: https://discordbots.org/bot/578372226252931072/vote"
                           "\n to vote, and use the command again to claim your reward!")
            return
        # 12h within the vote
        if voter[0]['claimed']:
            if datetime.now() > (voter[0]["date"]):
                await ctx.send("You can vote again! Go to: https://discordbots.org/bot/578372226252931072/vote"
                               "\n to vote, and use the command again to claim your reward!")
                return
            output = str(voter[0]["date"] - datetime.now())
            output = output[:output.find(".")].strip()
            await ctx.send(f"You can vote again in {output} hours")
            return

        amount = 5000
        cog = self.bot.get_cog("DonorCog")
        donor = cog.get_user(ctx.author.id)
        if donor:
            amount += 5000 * (donor["permission"] + 1)
        await ctx.db.execute("UPDATE voters SET claimed = $1 WHERE user_id = $2 AND bot_id = $3 AND type = $4", True,
                             ctx.author.id, 578372226252931072, "upvote")
        # if user voted, add entries in database + reward
        await ctx.send("You've successfully voted! You've been rewarded {} {}"
                       .format(amount, ctx.server_settings["EconomyCog"]["currency"]["value"]))
        await economy.update_currency(ctx.db, ctx.message.author, ctx.cluster_id, amount)


def setup(bot):
    global logger
    logger = logging.getLogger('bot')
    bot.add_cog(PublicCog(bot))
