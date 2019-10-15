import discord
from discord.ext import commands
import asyncpg
import logging
import sys, traceback
import aiohttp
import aioredis
from context import Context
import datetime
import asyncio
from utils.leaderboard import leaderboard
from utils.prefix import Prefix
import json
import config
import time
from http import client
initial_extensions = ["cogs.leaderboard", "cogs.owner", "cogs.marriage", "cogs.general", "cogs.pickup", "cogs.shop",
                      "cogs.automod", "cogs.fun", "cogs.dashboard", "cogs.public", "cogs.donor", "cogs.economy",
                      "cogs.setup", "cogs.stats", "cogs.rpg"]

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    handlers=[
                        #logging.FileHandler("/home/ec2-user/logs/discord.log", mode='w'),
                        logging.StreamHandler()
                    ])


# Handles custom prefixing



def _prefix_callable(bot, msg):
    user_id = bot.user.id
    base = [f'<@!{user_id}> ', f'<@{user_id}> ']
    if msg.guild is None:
        base.append('.')
    else:
        base.extend(bot.prefixes.get(msg.guild.id, ['.']))
    return base

class Db(object):
    def __init__(self, uri, loop):
        self.redis_adress = uri
        self.loop = loop
        self.loop.create_task(self.create())

    async def create(self):
        self.redis = await aioredis.create_redis(self.redis_adress, encoding='utf8')

# The custom bot class! Subclassed from commands.Bot
class Thor(commands.AutoShardedBot):

    def __init__(self):
        super().__init__(command_prefix=_prefix_callable, owner_id=394859035209498626)
        self.remove_command('help')
        self.prefixes = Prefix(self)
        self.addons = ["OwnerCog", "LeaderboardCog", "MarriageCog", "EconomyCog", "GeneralCog", "PickupCog", "ShopCog",
                       "AutomodCog", "FunCog", "DashboardCog", "PublicCog", "DonorCog", "StatsCog", "SetupCog", "RPGCog"]
        self.safe_timer = 60
        self.command_help = {}
        self.timed = {}

        # Loads cogs
        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()
            else:
                print(f'Successfully loaded {extension}')
        
        # Initiate a session (For manual API calls)
        
        self.session = aiohttp.ClientSession(loop=self.loop)

        # Creates a background tasks (Sets up the database entries)
        self.loop.create_task(self.latency_timer())
        self.loop.create_task(self.command_helper())

        # Initiates the database class, which lets us communicate with Redis <3 (Redis is love btw)
        self.db = Db(config.redis_path, self.loop)

        self.reset_date = {}
        print("Fenrir has Initialized")

    async def command_helper(self):
        await self.wait_until_ready()
        with open("command_help.json") as f:
            self.command_help = json.load(f)


    async def latency_timer(self):
        await self.wait_until_ready()
        while True:
            for latency in self.latencies:
                print(f"Shard {latency[0]}: {latency[1]}s")
            await asyncio.sleep(60)

    async def clean_addons(self, guild):
        cog = self.get_cog("LeaderboardCog")
        cog.del_reset_date(guild.id)

        print(f"REM {guild.name}")
        if guild.id in self.reset_date:
            del self.reset_date[guild.id]

        """ REDIS REMOVAL """
        await self.db.redis.delete("server:{}:addons".format(guild.id))
        await self.db.redis.delete("server:{}:settings".format(guild.id))
        features = ['image_check']
        for feature in features:
            await self.db.redis.delete("server:{}:automod:{}".format(guild.id, feature))
        await self.db.redis.delete("server:{}:automod".format(guild.id))


        """ SQL REMOVAL """
        async with self.pool.acquire() as c:
            await c.execute("DELETE FROM RESET WHERE guild_id = $1", guild.id)
            await c.execute("DELETE FROM economy WHERE server_id = $1", guild.id)
            await c.execute("DELETE FROM leaderboard WHERE server_id = $1", guild.id)
            await c.execute("DELETE FROM cooldowns WHERE server_id = $1", guild.id)
            await c.execute("DELETE FROM global_leaderboard WHERE guild_id = $1", guild.id)
            await c.execute("DELETE FROM items WHERE guild_id = $1", guild.id)
            await c.execute("DELETE FROM marriage WHERE guild_id = $1", guild.id)
            await c.execute("DELETE FROM convert WHERE guild_id = $1", guild.id)
            await c.execute("DELETE FROM addons WHERE guild_id = $1", guild.id)
            await c.execute("DELETE FROM automod WHERE guild_id = $1", guild.id)
            await c.execute("DELETE FROM settings WHERE guild_id = $1", guild.id)


        print(f"REM OK {guild.name}")



    async def on_command_error(self, ctx, error):

        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            prefix = self.prefixes.get(ctx.guild.id)
            if prefix:
                prefix = prefix[0]
            else:
                prefix = "."
            name = ctx.command.name
            if ctx.command.parent:
                name = ctx.command.parent.name
            usage = self.command_help[name]["usage"]
            string = ""

            for example in self.command_help[name]["examples"]:
                string += "``"+prefix+example[1:]+"``\n"
            fields = [("Examples:", string)]
            await ctx.send(f"You entered the command incorrectly.\nCorrect Format: ``{prefix}{name} {usage}``", image=False, add_fields=fields)

        if isinstance(error, commands.CheckFailure):
            if str(error) == "donor":
                await ctx.send("Only certain premium users can use this command."
                               " More info at:\nhttps://www.patreon.com/Hampe", image=False)
            else:
                await ctx.send("You don't have permission to use this command", image=False)
        if isinstance(error, commands.CommandInvokeError):
            # If the int is too big
            if isinstance(error.original, OverflowError):
                await ctx.send("You entered a too big number, try again with something lesser", image=False)
                return
            # Trying to store a bigger number in database than a bigint allows
            if isinstance(error.original, asyncpg.NumericValueOutOfRangeError) or isinstance(error.original, asyncpg.DataError):
                await ctx.send("Can't perform this action due to the limitations of your bank", image=False)
                return

            print(type(error.original))
            if isinstance(error.original, client.HTTPException) or \
                    isinstance(error.original, discord.errors.HTTPException):
                print(error)
                return
            try:
                print(f"CommandInvokeError. Server: {ctx.guild}. Command: {ctx.command}. "
                      f"User: {ctx.author}", error, error.__dict__)
            except Exception:
                print(f"CommandInvokeError, Command doesn't exist to any server?")
            

    # Boring custom prefix function 1
    def get_raw_guild_prefixes(self, guild_id):
        return self.prefixes.get(guild_id, [])

    # Boring custom prefix function 2
    async def set_guild_prefix(self, guild, prefix):
        self.prefixes.put(guild.id, prefix)

    # Custom written get_context function to implement custom aliasing

    async def get_context(self, message, *, cls=commands.Context):
        view = commands.view.StringView(message.content)
        ctx = cls(prefix=None, view=view, bot=self, message=message)

        if self._skip_check(message.author.id, self.user.id):
            return ctx

        prefix = await self.get_prefix(message)
        invoked_prefix = prefix

        if isinstance(prefix, str):
            if not view.skip_string(prefix):
                return ctx
        else:
            invoked_prefix = discord.utils.find(view.skip_string, prefix)
            if invoked_prefix is None:
                return ctx

        invoker = view.get_word()
        ctx.invoked_with = invoker
        ctx.prefix = invoked_prefix
        # -------------------------------------------------------------------
        # Checks if there's any command registered to the alias that you're invoking
        
        # If there is, the alias key contains the original callback functions name, and assigns the command
        # to the Context. This will make sure that every server can have unique names for the commands, but 
        # will still have the same functionality across every server

        # Oh, and also save the custom invoker in case we need it later
        # (Will be needed when printing out help texts for users)
        ctx.command = self.all_commands.get(invoker)
        return ctx

    # This runs for every message typed
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild:
            # Retrieves server settings
            server_settings = await self.db.redis.get('server:{}:settings'.format(message.guild.id))

            # In case someone chats before settings have been configured, return
            if not server_settings:
                return
            
            server_settings = json.loads(server_settings)

            # Get the active addons for the server
            addons = await self.db.redis.smembers('server:{}:addons'.format(message.guild.id))
            # Fetch the cog that handle the resetting
            cog = self.get_cog("LeaderboardCog")
            # Acquire a connection from the pool
            async with self.pool.acquire() as c:
                try:
                    await cog.update(message.guild, c, server_settings)
                except Exception:
                    print("Hitting error")
                    # Should return if reset dates are not set-up yet
                    return

                # should make the lb work in the main chats ONLY
                for addon in addons:
                    
                    # Every feature that should trigger from solely a message being typed, should be registered here:
                    if addon == "AutomodCog":
                        features = ['image_check']
                        for feature in features:
                            channels = await self.db.redis.smembers('server:{}:automod:{}'.format(message.guild.id, feature))
                            if channels:
                                cog = self.get_cog("AutomodCog")
                                await cog.message_check(message, feature, channels)

                    if addon == "LeaderboardCog":
                        try:
                            channels = server_settings["LeaderboardCog"]["channel"]["value"]
                        except Exception as e:
                            print(e)
                            return
                        if channels:
                            timed = self.timed.get(message.author.id)
                            if timed:
                                print(f"User: {message.author.name}, ID: {message.author.name}, Time: {datetime.datetime.now()}")
                            cog = self.get_cog("LeaderboardCog")
                            if "all" in channels:
                                await leaderboard.adder(c, message, cog)
                            elif f"{message.channel.id}" in channels:
                                await leaderboard.adder(c, message, cog)
            # When commands should be handled
            await self.process_commands(message, addons, server_settings)

    
    # Will process the commands
    async def process_commands(self, message, addons=None, settings=None):
        if not addons:
            print("There are no addons to be processed, returning")
            return
        if not settings:
            print("There are no addon settings to be processed, returning")
            return

        # Grabs the context from the function above (also with a custom Context class)
        ctx = await self.get_context(message, cls=Context)
        if ctx.command is None:
            return
        # If we got any value, we continue towards command execution
        if ctx.command.cog_name in addons:
        # Handles the opening and closing of the pooled connection (part of the custom Context class)
            # Grabs settings for the specific command (command_settings and embed_settings)
            # Checks if the command has sub-commands

                #Loops through all the subcommands
                #If none of the subcommands where invoked
                #this will always return to the 
                    
        
            # If the settings are found (Should ALWAYS be found in the live version) we decode the json into a dict and pass it into the Context for invokation
            
            ctx.addons = addons
            # Here we assign the actual addon settings to the Context before invoking.
            ctx.server_settings = settings
            cog = self.get_cog("DonorCog")
            ctx.donor = cog.get_user(ctx.author.id)
            #print(ctx.server_settings["EconomyCog"]["currency"])

            
            async with ctx.acquire():
                perks = await ctx.db.fetch("SELECT name FROM items WHERE guild_id = $1 AND member_id = $2 AND type = $3", ctx.guild.id, ctx.author.id, 1)

                ctx.perks = [x["name"] for x in perks]
                # Invoking the Context (Basically let's us execute the command)
                await self.invoke(ctx)
        else:
            print("Addon is not active on this server")
            print(f"{ctx.command.module} is not active, command disabled")

    async def on_member_join(self, member):
        if member.guild.id != 472546414455685132:
            return
        cog = self.get_cog("DonorCog")
        for i, role in enumerate(cog.get_donor_roles()):
            if role in member.roles:
                print("Assigning Member to internal donor list (on_member_join)")
                await cog.assign(member.id, i)

    async def on_member_update(self, before, after):
        # Return if it's not Asgard
        if before.guild.id != 472546414455685132:
            return
        # Return if roles has not been changed
        if before.roles == after.roles:
            return

        cog = self.get_cog("DonorCog")
        for i, role in enumerate(cog.get_donor_roles()):
            # If the role didn't exist before
            if role not in before.roles:
                # And the role exists now
                if role in after.roles:
                    print("Assigning Member to internal donor list (on_member_update)")
                    await cog.assign(after.id, i)
            # If the role existed before
            if role in before.roles:
                # But does not exist anymore
                if role not in after.roles:
                    try:
                        await cog.remove(after.id)
                    except Exception:
                        pass


    async def on_guild_join(self, guild):
        setup = self.get_cog("SetupCog")
        await setup.setup_addons(guild)

    async def on_guild_remove(self, guild):
        await self.clean_addons(guild)

    async def login(self, token, *args, bot=True):
        #log.info('logging in using static token')
        result = await self.http.static_login(token, bot=bot)
        self._connection.is_bot = bot

    async def on_ready(self):
        """Executes whenever the bot is ready"""
        await self.change_presence(status=discord.Status.online, activity=discord.Game(f"with {len(self.guilds)} Realms"))
        setup = self.get_cog("SetupCog")
        await setup.setup_addons()
        print(f'Ready: {self.user} (ID: {self.user.id})')
        print(discord.__version__)
        print('------')

    async def close(self):
        print("closing")
        await super().close()
        await self.session.close()
