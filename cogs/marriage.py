from discord.ext import commands
import datetime
from utils.leaderboard import leaderboard
import json
from utils.embeds import embedmanager
from utils.economy import economy
from utils.marriage import marriage
from datetime import datetime

class MarriageCog(commands.Cog):
    def __init__(self, bot):
        self.bot=bot
    
    @commands.command(name="marry")
    async def marry(self, ctx):
        coins=10000
        #output=datetime.strftime(date, "%b %d, %Y %I:%M %p") #Time format
        try:
            target=ctx.message.mentions[0]
        except(ValueError, IndexError):
            raise commands.BadArgument
        if target.bot:
            await ctx.send("You can't marry bots", image=False)
            return
        if target.id==ctx.message.author.id:
            await ctx.send("You can't marry yourself", image=False)
            return
        currency = await economy.get_currency(ctx.db, ctx.message.author, ctx.cluster_id)
        currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
        if currency>=coins:
            check = await marriage.send_request(ctx.db, ctx.message.author.id, target.id, ctx.guild.id)
            if check:
                if (check["send_id"]==ctx.message.author.id or check["rec_id"]==ctx.message.author.id) and (check["send_id"]==target.id or check["rec_id"]==target.id) and check["status"]==0:
                    await ctx.send("You already have a pending request with this user", image=False)
                    return
                elif (check["send_id"]==ctx.message.author.id or check["rec_id"]==ctx.message.author.id) and (check["send_id"]==target.id or check["rec_id"]==target.id) and check["status"]==1:
                    await ctx.send("You are already married to this user!", image=False)
                    return
                elif (check["send_id"]==ctx.message.author.id or check["rec_id"]==ctx.message.author.id) and check["status"]==1:
                    await ctx.send("You are already married! You can't marry more than one user at a time", image=False)
                    return
                await ctx.send("This user is already married! You can't marry more than one user at a time", image=False)
                return

            await economy.update_currency(ctx.db, ctx.message.author, ctx.cluster_id, -coins)
            field=[("Awaiting "+target.name+"'s response...", ".accept "+ctx.message.author.mention+" to accept\n.decline "+ctx.message.author.mention+" to decline")]
            await ctx.send(f"You purchased a ring for {coins} {currency_name} and proposed to {target.name} {target.mention}!", add_fields=field)
        else:
            await ctx.send(f"You don't have enough {currency_name}. The marriage cost is {coins} {currency_name}", image=False)
    @commands.command(name="accept")
    async def accept_request(self, ctx):
        try:
            target=ctx.message.mentions[0]
        except (ValueError, IndexError):
            raise commands.BadArgument
        # All the entries you're involced in
        check = await marriage.accept_request(ctx.db, ctx.message.author.id, target.id, ctx.guild.id)
        if not check:
            await ctx.send("You don't have a pending request from that user", image=False)
            return
        await marriage.remove_request(ctx.db, ctx.message.author.id, 0, ctx.guild.id)
        await marriage.remove_request(ctx.db, target.id, 0, ctx.guild.id)
        await ctx.send(f"Congratulations!\n{ctx.message.author.mention} and {target.mention} are now married.")

    @commands.command(name="decline")
    async def decline_request(self, ctx):
        try:
            target=ctx.message.mentions[0]
        except (ValueError, IndexError):
            raise commands.BadArgument
        check = await marriage.decline_request(ctx.db, ctx.message.author.id, target.id, ctx.guild.id)
        if not check:
            await ctx.send("You don't have a pending request from that user", image=False)
            return
        await ctx.send("You declined the proposal and flushed the ring.")
    @commands.command(name="marriage")
    async def display_marriage(self, ctx):
        try:
            target = ctx.message.mentions[0]
        except (ValueError, IndexError):
            target = ctx.message.author
        entry = await marriage.get_marriage(ctx.db, target.id, ctx.guild.id)
        if not entry:
            if target == ctx.message.author:
                await ctx.send("You're not married to anyone", image=False)
            else:
                await ctx.send(f"{target.mention} is not married to anyone", image= False)
            return
        rec_id=entry[0]['rec_id']
        send_id=entry[0]['send_id']
        date=entry[0]['date']
        date=datetime.strftime(date, "%b %d, %Y %I:%M %p") #Time format
        await ctx.send(f"<@{rec_id}> and <@{send_id}> have been married since\n{date}")
    @commands.command(name="divorce")
    async def divorce(self, ctx):
        check = await marriage.remove_request(ctx.db, ctx.message.author.id, 1, ctx.guild.id)
        if not check:
            await ctx.send("You're so lonely you don't even have anyone to divorce", image=False)
            return
        await ctx.send("You divorced and flushed the ring.\nTime to move on!")
        

        
def setup(bot):
    bot.add_cog(MarriageCog(bot))