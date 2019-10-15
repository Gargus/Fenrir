from discord.ext import commands
import datetime
from utils.embeds import embedmanager
from utils.economy import economy
import json
import asyncio
import discord
import config
import utils.checks as checks
import aioredis
import sys

class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot=bot

    def check_if_op(ctx):
        if ctx.author.id == 465976233251962900:
            return True
        perms = {'manage_guild': True}
        ch = ctx.channel
        permissions = ch.permissions_for(ctx.author)
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm, None) != value]
        
        if not missing:
            return True
        else:
            return False

    async def logging(self, ctx):
        log_channel = ctx.bot.get_channel(478610371435954200)
        embed = discord.Embed(description=f"Server: ``{ctx.guild}``, Channel: ``{ctx.channel}``, User: ``{ctx.author}``, Command: ``{ctx.command}``, Message: ``{ctx.message.content}``")
        embed.set_footer(text=str(ctx.message.created_at).split(".")[0])
        try:
            await log_channel.send(embed=embed)
        except Exception:
            pass

    @commands.command(name="reload")
    @commands.is_owner()
    async def reloaded(self, ctx, choice):
        # Import JSON command file

        if choice == "addons":
            for guild in self.bot.guilds:

                settings = await self.bot.db.redis.get('server:{}:settings'.format(guild.id))
                settings = json.loads(settings)
                # Key = EconomyCog
                for key, value in settings.items():
                    # print(key, value)
                    # Key = currency
                    for key2, value2 in value.items():
                        new_value = value2.get("value", None)
                        if new_value is not None:
                            settings[key][key2] = {"value": new_value}
                        else:
                            for key3, value3 in value2.items():
                                new_value = value3.get("value", None)
                                if new_value is not None:
                                    settings[key][key2][key3] = {"value": new_value}
                # print(json.dumps(settings), type(json.dumps(settings)))
                await self.bot.db.redis.set('server:{}:settings'.format(guild.id), json.dumps(settings))


        if choice=="commands":
            with open("commands.json") as f:
                entries = json.load(f)
            for guild in self.bot.guilds:
                print(f"Reloading: {guild}")
                # Grabs earlier commands
                # Grabs info from default template
                for name, entry in entries.items():     
                    # Add the command, and it's settings to the database
                    await self.bot.db.redis.set('server:{}:command:{}'.format(guild.id, name), json.dumps(entry))

    @commands.command(name="eval")
    @commands.is_owner()
    async def eval_me(self, ctx, string: str):
        result = str(eval(string))
        await ctx.send(result)

    @commands.group(name="channel", invoke_without_command=True)
    @commands.check(check_if_op)
    async def channel(self, ctx):
        await self.logging(ctx)
        prefix = self.bot.prefixes.get(ctx.message.guild.id)
        if not prefix:
            prefix= ["."]
        prefix=prefix[0]
        await ctx.send(f"Available options: ``add``, ``remove``\nAvailable features: ``image_check``\nFormat: ``{prefix}channel`` ``[option]`` ``[feature]`` ``[#channel]``")

    @channel.command(name="add")
    @commands.check(check_if_op)
    async def channel_add(self, ctx, feature, channel: discord.TextChannel):
        await self.logging(ctx)
        features = ["image_check"]
        feature=feature.lower()
        if feature not in features:
            await ctx.send("That's not an available feature")
            return
        if channel:
            check = await self.bot.db.redis.smembers('server:{}:automod:{}'.format(ctx.guild.id, feature))
            if check:
                if str(channel.id) in check:
                    await ctx.send("You've already added this feature to this channel.")
                    return
                new_channels = check
                new_channels.append(str(channel.id))

                await ctx.db.execute("UPDATE automod SET channel_id = $1 WHERE guild_id = $2 AND feature = $3", new_channels, ctx.guild.id, feature)
            else:
                check2 = await ctx.db.fetch("SELECT * FROM automod WHERE guild_id = $1 AND feature = $2", ctx.guild.id, feature)
                if not check2:
                    await ctx.db.execute("INSERT INTO automod (guild_id, feature, channel_id) VALUES ($1, $2, $3)", ctx.guild.id, feature, [str(channel.id)])
                else:
                    await ctx.db.execute("UPDATE automod SET channel_id = $1 WHERE guild_id = $2 AND feature = $3",
                                         [str(channel.id)], ctx.guild.id, feature)

            await self.bot.db.redis.sadd("server:{}:automod:{}".format(ctx.message.guild.id, feature), channel.id)
            await ctx.send(f"Added feature ``{feature}`` to channel: ``{channel}``")


    @channel.command(name="remove")
    @commands.check(check_if_op)
    async def channel_remove(self, ctx, feature, channel: discord.TextChannel):
        await self.logging(ctx)
        features = ["image_check"]
        feature=feature.lower()
        if feature not in features:
            await ctx.send("That's not an available feature")
            return
        if channel:
            check = await self.bot.db.redis.smembers('server:{}:automod:{}'.format(ctx.guild.id, feature))
            if str(channel.id) not in check:
                await ctx.send("This channel did not have this feature active.")
                return
            new_channels = check
            new_channels.remove(str(channel.id))
            await ctx.db.execute("UPDATE automod SET channel_id = $1 WHERE guild_id = $2 AND feature = $3", new_channels, ctx.guild.id, feature)

            await self.bot.db.redis.srem("server:{}:automod:{}".format(ctx.message.guild.id, feature), channel.id)
            await ctx.send(f"Removed feature ``{feature}`` from channel: {channel}")


    @commands.group("reward", invoke_without_command=True)
    @commands.check(checks.check_if_op)
    async def reward(self, ctx, user, amount: int):
        await self.logging(ctx)
        if amount <= 0:
            raise commands.BadArgument
        try:
            target = ctx.message.mentions[0]
        except (ValueError, IndexError):
            await ctx.send("You have to tag someone to use this command", image=False)
            return
        await economy.update_currency(ctx.db, target, ctx.cluster_id, amount)
        currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
        await ctx.send(f"You rewarded {target.mention} with `{amount}` {currency_name}.")

    @commands.group("cluster", invoke_without_command=True)
    @commands.is_owner()
    async def cluster(self, ctx):
        await ctx.send("Available options: ``add``, ``rem``")

    @cluster.command(name="add")
    @commands.is_owner()
    async def cluster_add(self, ctx, cluster_id: int):
        await ctx.db.execute("INSERT INTO cluster (guild_id, cluster_id, name) VALUES ($1, $2, $3)", ctx.guild.id, cluster_id, ctx.guild.name)
        await ctx.send(f"Added guild: ``{ctx.guild.name}`` to cluster: ``{cluster_id}``")

    @cluster.command(name="rem")
    @commands.is_owner()
    async def cluster_rem(self, ctx, cluster_id: int):
        await ctx.db.execute("DELETE FROM cluster WHERE guild_id = $1 AND cluster_id = $2", ctx.guild.id, cluster_id)
        await ctx.send(f"Removed guild: ``{ctx.guild.name}`` from cluster: ``{cluster_id}``")

    @commands.command()
    @commands.is_owner()
    async def members(self, ctx):
        number = 0
        for member in self.bot.get_all_members():
            number+=1
        await ctx.send(f"This bot currently handles {number} users.")


    @commands.command()
    @commands.is_owner()
    async def servers(self, ctx):
        string = ""
        counter=0
        for guild in self.bot.guilds:
            counter+=1
            string+=f"Name: {guild.name}, ID: {guild.id}, Count: {guild.member_count}, Owner: {guild.owner}\n"
            if counter>=10:
                await ctx.send(string)
                counter=0
                string=""
        await ctx.send(string) 


    @commands.command()
    @commands.check(check_if_op)
    async def strip(self, ctx, user, amount: int):
        await self.logging(ctx)
        if amount<=0:
            raise commands.BadArgument
        try:
            target = ctx.message.mentions[0]
        except (ValueError, IndexError):
            await ctx.send("You have to tag someone to use this command", image=False)
            return
        await economy.update_currency(ctx.db, target, ctx.cluster_id, -amount)
        currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
        await ctx.send(f"You stripped {target.mention} off of `{amount}` {currency_name}.")              

    @commands.is_owner()
    @commands.group(name="sql", invoke_without_command=True)
    async def sql(self, ctx, query:str):
        print(query)
    @commands.is_owner()
    @sql.command(name="execute")
    async def execute(self, ctx, query:str):
        result = await ctx.db.execute(query)
        await ctx.send(str(result))
    @commands.is_owner()
    @sql.command(name="fetch")
    async def fetch(self, ctx, query:str, limit=1):
        query=query + " LIMIT {}".format(limit)
        results = await ctx.db.fetch(query)
        for result in results:
            result=dict(result)
            description=""
            for name, value in zip(result, result.values()):
                description+=f"**{name.title()}:** {value}, "
            await ctx.send(description)

    @commands.is_owner()
    @commands.group(name="redis", invoke_without_command=True)
    async def redis(self, ctx):
        await ctx.send("Current options: ``get``,``set``, ``sadd``, ``smembers``, ``delete``, ``srem``")
    @commands.is_owner()
    @redis.command(name="set")
    async def _set(self, ctx, key, value):
        status = await self.bot.db.redis.set(key, value)
        await ctx.send(str(status))
    @commands.is_owner()
    @redis.command(name="get")
    async def _get(self, ctx, key):
        result = await self.bot.db.redis.get(key)
        await ctx.send(str(result))
    @commands.is_owner()
    @redis.command(name="sadd")
    async def sadd(self, ctx, key, value):
        status = await self.bot.db.redis.sadd(key, value)
        await ctx.send(str(status))
    @commands.is_owner()
    @redis.command(name="smembers")
    async def smembers(self, ctx, key):
        result = await self.bot.db.redis.smembers(key)
        await ctx.send(str(result))
    @commands.is_owner()
    @redis.command(name="delete")
    async def delete(self, ctx, key):
        result = await self.bot.db.redis.delete(key)
        await ctx.send(str(result))
    @commands.is_owner()
    @redis.command(name="srem")
    async def srem(self, ctx, key, value):
        result = await self.bot.db.redis.srem(key, value)
        await ctx.send(str(result))
        


def setup(bot):
    bot.add_cog(OwnerCog(bot))