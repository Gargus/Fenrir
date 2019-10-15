import datetime
import json
import copy
from sys import getsizeof
from discord.ext import commands

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Run when database setup + redis migration is done
    async def setup_cogs(self):
        await self.setup_helper()
        for addon in self.bot.addons:
            cog = self.bot.get_cog(addon)
            try:
                self.bot.loop.create_task(cog.main_setup())
            except AttributeError:
                continue
            print(f"{addon} main_setup done")

    # Loops through every entry till it finds value
    # Have to compare the settings with the new template somehow
    # Replace the settings in the database

    async def addon_fixer(self, template, settings):
        print("Running fixer")
        # Should run until we got check
        paths = []
        # Runs for every addon in the start
        # We know for a fact we will not have a value here
        for key, value in settings.items():

            # This will run for every cog entry
            path = [key]
            iterator = value.items()
            running = True

            while running:

                running = False
                # We might get multiple entries that contains value, keep that in mind
                for _key, _value in iterator:
                    path.append(_key)
                    check = _value.get("value", None)

                    # If it is found
                    if check is not None:
                        # Continue to next value, but we need to store the path and the value
                        path.append("value")
                        location = {'path': path, 'value': check}
                        path = [key]
                        paths.append(location)
                        continue
                    else:
                        iterator = _value.items()
                        running = True

        # Magical code that places the path values into it's correct position
        full_template = copy.deepcopy(template["settings"])
        for path in paths:
            tmp = full_template
            for key in path['path']:
                if key == "value":
                    tmp[key] = path['value']
                try:
                    tmp = tmp[key]
                except KeyError:
                    break
        print("Fixer done")
        return json.dumps(full_template)
        #await self.bot.db.redis.set('server:{}:settings'.format(guild_id), json.dumps(full_template))
        #print(json.dumps(full_template, indent=4, sort_keys=True))


    async def setup_helper(self):
        for addon in self.bot.addons:

            await self.bot.db.redis.delete('bot:addon:{}:commands'.format(addon.split("Cog")[0]))
        with open("command_help.json") as f:
            commands = json.load(f)

        for key, value in commands.items():
            value["name"] = key
            await self.bot.db.redis.sadd('bot:addon:{}:commands'.format(value["addon"]), json.dumps(value))

    # Sync Postgres to Redis for LIVE data usage
    async def setup_redis(self):
        async with self.bot.pool.acquire() as c:
            print("Redis MIGRATE start")
            # Empties the entire key-store
            await self.bot.db.redis.flushdb()

            # Adds the documentation for the website


            # Addon Sync
            all_addons = await c.fetch("SELECT * FROM addons")
            for single_addon in all_addons:
                for addon in single_addon["addons"]:
                    await self.bot.db.redis.sadd('server:{}:addons'.format(single_addon["guild_id"]), addon)

            # Setting Sync
            all_settings = await c.fetch("SELECT * FROM settings")
            for setting in all_settings:
                await self.bot.db.redis.set('server:{}:settings'.format(setting["guild_id"]), setting["settings"])

            # Automod Sync
            all_features = await c.fetch("SELECT * FROM automod")
            for feature in all_features:
                for channel in feature["channel_id"]:
                    await self.bot.db.redis.sadd("server:{}:automod:image_check".format(feature["guild_id"]), channel)

            # Donor sync
            donors = await c.fetch("SELECT * FROM donors")
            for donor in donors:
                for guild_id in donor["aw_guild_id"]:
                    await self.bot.db.redis.set("member:{}:guild:{}:work_task".format(donor["member_id"], guild_id), 1)
                quote = donor["quote"]
                if not quote:
                    quote = "No quote registered"
                await self.bot.db.redis.set("member:{}:quote".format(donor["member_id"]), quote)

            print("redis MIGRATE end")

            # Runs the setup of cogs once the migration is done
            await self.setup_cogs()

    # Setup addons will mainly check if certain settings are missing from the database,
    # that should be there for every server. If it's booting up for the first time, it will also put
    # all of these values into the redis key-value store to be used for live-processing when the bot is running.

    async def setup_addons(self, _guild=None):
        await self.bot.wait_until_ready()
        print("Setting up addons for...")
        addons = self.bot.addons

        with open("addons.json") as f:
            addon_entries = json.load(f)
            # Size of template. Use this to know when addon_fixer should be called
            addon_size = len(str(addon_entries))
        async with self.bot.pool.acquire() as c:

            lbcog = self.bot.get_cog("LeaderboardCog")

            """ GLOBAL RESET """

            date = await c.fetch("SELECT date from RESET where guild_id=$1", 1337)
            if not date:
                next_week = lbcog.get_weekstart(datetime.datetime.now())
                await c.execute("INSERT INTO RESET (guild_id, date) VALUES ($1, $2)", 1337, next_week)
                lbcog.set_reset_date("GLOBAL", next_week)
                # self.bot.reset_date["GLOBAL"] = next_week
            else:
                lbcog.set_reset_date("GLOBAL", date[0]["date"])
                # self.bot.reset_date["GLOBAL"] = date[0]["date"]

            # Considering the commands will always be the same, no matter if boot-up or not
            # a list with all the command names should be enough to work with
            # should run once

            guilds = []
            # If guild, only iterate over the single guild
            if _guild:
                guilds.append(_guild)

            # If no guild, iterate over all guilds
            else:
                guilds = self.bot.guilds

            for guild in guilds:
                print(f"Setting up {guild.name}...")


                """ ADDONS """
                # Adds new addons
                all_addons = await c.fetch("SELECT * FROM addons WHERE guild_id = $1", guild.id)
                if not all_addons:
                    # defaults to all active addons
                    await c.execute("INSERT INTO addons (guild_id, addons) VALUES ($1, $2)", guild.id, addons)
                    if _guild:
                        for addon in addons:
                            await self.bot.db.redis.sadd('server:{}:addons'.format(guild.id), addon)
                else:
                    for addon in addons:
                        check = [x for x in all_addons[0]["addons"] if x == addon]
                        if not check:
                            await c.execute("UPDATE addons SET addons = $1 WHERE guild_id = $2", addons, guild.id)
                            break

                # If server without settings, create settings and keep the old ones as they are


                add_settings = await c.fetch("SELECT * FROM settings WHERE guild_id = $1", guild.id)
                if not add_settings:
                    # Grabs entries from default template
                    for entry in addon_entries.values():
                        await c.execute("INSERT INTO settings (guild_id, settings, size) VALUES ($1, $2, $3)", guild.id,
                                        json.dumps(entry), addon_size)
                        await self.bot.db.redis.set('server:{}:settings'.format(guild.id),  json.dumps(entry))

                else:
                    if add_settings[0]["size"] != addon_size:
                        new_template = await self.addon_fixer(addon_entries, json.loads(add_settings[0]["settings"]))
                        await c.execute("UPDATE settings SET size = $1, settings = $2 WHERE guild_id = $3",
                                        addon_size, new_template, guild.id)
                        # Check if new things have been added to the template, and att those parts



                """ GUILD RESET """

                date = await c.fetch("SELECT date from RESET where guild_id=$1", guild.id)
                if not date:
                    next_week = lbcog.get_weekstart(datetime.datetime.now())
                    await c.execute("INSERT INTO RESET (guild_id, date) VALUES ($1, $2)", guild.id, next_week)
                    lbcog.set_reset_date(guild.id, next_week)
                    # self.bot.reset_date[guild.id] = next_week
                else:
                    lbcog.set_reset_date(guild.id, date[0]["date"])
                    # self.bot.reset_date[guild.id] = date[0]["date"]

                print(f"{guild.name} is set up.")

        # To make sure this only runs at boot-up
        if _guild is None:
            await self.setup_redis()


        print("Addons setup complete.")


def setup(bot):
    bot.add_cog(SetupCog(bot))
