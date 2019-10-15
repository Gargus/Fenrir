from discord.ext import commands
from datetime import datetime, timedelta
from utils.leaderboard import leaderboard
import utils.reset as reset
import discord


class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset_dates = {}
        self.history = {}

    def set_reset_date(self, guild_id, date):
        self.reset_dates[guild_id] = date

    def del_reset_date(self, guild_id):
        if guild_id in self.reset_dates:
            del self.reset_dates[guild_id]

    @staticmethod
    def get_weekstart(date):
        return reset.weekstart(date)

    async def output(self, c, guild=None, settings=None):
        if guild:
            data = await reset.result_output(c, guild.id)
        else:
            data = await reset.result_output(c)
        embed = None
        string = ""
        for entry in data:
            value = entry["value"]
            if guild:
                usage = self.bot.get_user(entry["member_id"])
            else:
                usage = self.bot.get_guild(entry["guild_id"])
            try:
                string += f"{usage} had {value} messages\n"
            except AttributeError:
                if guild:
                    string += "<@{}> had {} messages\n".format(entry["member_id"], value)

                else:
                    string += str(entry["guild_id"]) + f" had {value} messages\n"

            if guild:
                embed = discord.Embed(title="Results for {}".format(guild.name), description=string)
            else:
                embed = discord.Embed(title="Results for Global", description=string)


        try:
            staff_channel = self.bot.get_channel(480798534409650186)
            if guild and settings:

                channel_id = settings["LeaderboardCog"]["result"]["value"]
                staff_channel = self.bot.get_channel(int(channel_id))

            if staff_channel:
                try:
                    await staff_channel.send(embed=embed)
                except Exception as e:
                    print(e)
                else:
                    print(f"Sent results to: {staff_channel}")

        except Exception as e:
            print("Tried sending results to staff channel but encountered:", e)


    async def update(self, guild, c, settings):
        today = datetime.now()
        if today > self.reset_dates["GLOBAL"]:
            print("Output Global Leaderboard")
            # Sends the results to the appropriate channel
            await self.output(c)

            # Deletes the leaderboard data and update the timers
            await c.execute("DELETE FROM global_leaderboard")
            next_week = reset.weekstart(today)
            self.reset_dates["GLOBAL"] = next_week
            await c.execute("UPDATE RESET SET date=$1 WHERE guild_id=$2", next_week, 1337)

        if today > self.reset_dates[guild.id]:
            print("Output {} Leaderboard".format(guild.name))
            await self.output(c, guild, settings)

            await c.execute("DELETE FROM convert WHERE guild_id = $1", guild.id)
            await c.execute("DELETE FROM leaderboard WHERE server_id=$1", guild.id)
            next_week = reset.weekstart(today)
            self.reset_dates[guild.id] = next_week
            await c.execute("UPDATE RESET SET date=$1 WHERE guild_id=$2", next_week, guild.id)

    @commands.command()
    async def uptime(self, ctx):

        desc="The bot has been running for "+str(datetime.utcnow()-self.bot.uptime)+" days, "
        await ctx.send(desc)

    @commands.command(name="time")
    @commands.is_owner()
    async def time_person(self, ctx, user_id:int):
        self.bot.timed[user_id] = True
        await ctx.send(f"User with id: {user_id} added to be timed")

    @commands.command(name="test")
    async def test(self, ctx):
        pass


    @commands.group(name="lb", invoke_without_command=True)
    async def lb(self, ctx):
        guild=ctx.cluster_id
        result = await leaderboard.get_top(ctx.db, 10, guild) 
        string=""
        for i, member in enumerate(result):
            user=self.bot.get_user(member['member_id'])
            id=member['member_id']
            value=str(member['value'])
            if user:
                string+=f'**{i+1}. {user.name} {user.mention}: {value} messages**\n'
            else:
                string+=f'**{i+1}. $This user ran!$ <@{id}>: {value} messages**\n'
        await ctx.send(string, title="Server Weekly Activity Leaderboard")

    @lb.command(name="global")
    async def global_leaderboard(self, ctx):
        result = await leaderboard.get_top(ctx.db, 10, None)
        string=""
        for i, member in enumerate(result):
            guild=self.bot.get_guild(member['guild_id'])
            id = member['guild_id']
            value=str(member['value'])
            if guild:
                string+=f'**{i+1}.** {guild}: **{value} messages**\n'
            else:
                string+=f'**{i+1}.** $This server died!$ <@{id}>: **{value} messages**\n'
        await ctx.send(string, title="Global Weekly Activity Leaderboard")

    @commands.group(name="rank", invoke_without_command=True)
    async def rank(self, ctx, mode: str=None):
        string=""
        guild=ctx.cluster_id
        try:
            check = int(mode)
        except (ValueError, IndexError, TypeError):
            try:
                string+=ctx.message.mentions[0].name+" "
                data = ctx.message.mentions[0].id
            except (ValueError, IndexError):
                data = ctx.message.author.id
                string+="You've "
            finally:
                lb_data = await leaderboard.get_pos(ctx.db, data, guild)
                string+=f"posted **{lb_data[0]}** messages this week\nCurrently rank **#{lb_data[1]}** on the server leaderboard."
        else:
            lb_data = await leaderboard.get_member(ctx.db, check, guild)
            if lb_data:
                user=self.bot.get_user(lb_data[1])
                value=lb_data[0]
                if user:
                    string+=f"{user.name} posted **{value}** messages this week\nCurrently rank **#{check}** on the server leaderboard."
                else:
                    string+=f"This user ran! posted **{value}** messages this week\nCurrently rank **#{check}** on the server leaderboard."
            else:
                string="There's no user with this rank"

        
        #em=embedmanager(ctx, string, "Weekly Activity Leaderboard")
        #await ctx.send(em[0], embed=em[1])
        await ctx.send(string)

def setup(bot):
    bot.add_cog(LeaderboardCog(bot))