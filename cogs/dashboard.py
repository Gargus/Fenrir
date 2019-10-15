from discord.ext import commands
import asyncio
import json
import re
import utils.checks as checks
import discord



class Prefix(commands.Converter):
    async def convert(self, ctx, argument):
        user_id = ctx.bot.user.id
        if argument.startswith((f'<@{user_id}>', f'<@!{user_id}>')):
            raise commands.BadArgument('That is a reserved prefix already in use.')
        return argument


class DashboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = {}
        self.bot.loop.create_task(self.settings_setup())

    async def on_ready(self):
        await self.settings_setup()

    async def settings_setup(self):
        with open("dashboard_settings.json") as f:
            self.settings = json.load(f)

    @commands.command(name="prefixswap")
    @commands.check(checks.check_if_op)
    async def prefix_add(self, ctx, pref: Prefix):
        try:
            await self.bot.set_guild_prefix(ctx.guild, pref)
        except Exception as e:
            print(e, "error")
        else:
            status = await ctx.db.execute("UPDATE prefix SET prefix = $1 WHERE guild_id = $2", pref, ctx.guild.id)
            if str(status) == "UPDATE 0":
                await ctx.db.execute("INSERT INTO prefix (guild_id, prefix) VALUES ($1, $2)", ctx.guild.id, pref)
            await ctx.send(f"You successfully changed your prefix to: ``{pref}``")

    @commands.check(checks.check_if_op)
    @commands.command()
    async def dashboard(self, ctx):
        string=""
        options = ["addons"]
        for option in options:
            string+=f"`{option}`\n"
        msg = await ctx.send("Select the type of settings you want to modify by typing the name", add_fields=[("Options:", string)])
        def check(m):
            if m.content in options:
                return m.author == ctx.message.author
        try:
            message = await self.bot.wait_for('message', timeout=20, check=check)
        except asyncio.TimeoutError:
            await msg.delete()
        else:
            await msg.delete()
            function = getattr(self, "dash_"+message.content)
            try:
                await message.delete()
            except Exception:
                pass
            await function(ctx)

    async def dash_addons(self, ctx):
        settings = ctx.server_settings
        help_strings = None
        key_order = []
        while True:
            addon = False
            options = []
            string=""
            if not settings.items():
                msg = await ctx.send("This addon is not configurable yet.")
                return
            for entry in settings.items():
                if entry[0] != "help_strings":
                    name = entry[0]
                    if entry[0].find("Cog")!=-1:
                        addon = True
                        name = entry[0].split("Cog")[0].lower()
                    # Temp disable of pickup settings
                    if name != "pickup":
                        options.append(name)
                        string+=f"`{name}`\n"
            if addon:
                msg = await ctx.send("Please select the addon by typing the name", add_fields=[("Addons:", string)])
            else:
                msg = await ctx.send("Please select the setting you want to modify by typing the name", add_fields=[("Settings:", string)])
            def check(m):
                if m.content in options:
                    return m.author == ctx.message.author
            try:
                message = await self.bot.wait_for('message', timeout=20, check=check)
            except asyncio.TimeoutError:
                await msg.delete()
                break
            else:
                if addon:
                    key = message.content.title()+"Cog"

                    # Could be here
                    settings = settings[key]
                    key_order.append(key)
                else:
                    key = message.content

                    # Could be here
                    settings = settings[key]
                    key_order.append(key)
                check = settings.get("value", None)
                try:
                    await message.delete()
                except Exception:
                    pass
                if check is not None:
                    await msg.delete()
                    await self.overwrite_setting(ctx, settings, key_order)
                    break

            await msg.delete()

    def mask_id(self, value):
        masked = re.findall(r'\d+', value)
        return masked[0]

    def get_name(self, guild, content, type):
        try:
            int(content)
        except Exception:
            return str(content)

        if type == "channel":
            channel = discord.utils.get(guild.channels, id=int(content))
            return "#" + channel.name
        else:
            return str(content)




    def regex_filter(self, type, content, listed):
        # split into more alternatives
        if listed:
            args = content.split(",")
            for i, arg in enumerate(args):
                tmp = arg.split(" ");
                for val in tmp:
                    if val:
                        args[i] = val
        else:
            args = content.split(" ")
            if len(args) >= 2:
                return

        switcher = {
            "string": r'(^[A-Za-z]+$)',
            "int": r'(^\d+$)',
            "channel": r'(<#[0-9]*>)',
            "member": r'(<@[0-9]*>)',
            "role": r'(<@&[0-9]*>)',
            "custom_emoji": r'(<a?:\w+:\d+>)',
            "emoji": r'(^:\w+:$)',
            "url": r'(^https:\/\/[!-z]*$)'
        }
        if type == "wildcard":
            return content
        elif content == "all":
            return content
        else:
            pattern = switcher.get(type, None)
            if not pattern:
                print("This type does not exist in the regex switcher...")
                return
            values = []
            if listed:
                for arg in args:
                    val = re.match(pattern, arg)
                    if val:
                        value = self.mask_id(val.group(0))
                        values.append(value)
            else:
                val = re.match(pattern, args[0])
                if val:
                    value = self.mask_id(val.group(0))
                    return value
            return values

    async def overwrite_setting(self, ctx, settings, key_order):
        old_values = ""
        listed = False
        int_settings = self.settings
        for key in key_order:
            int_settings = int_settings[key]
        if int_settings["dtype"] == "list":
            listed = True
        if listed and settings["value"] != "all":
            for ent in settings["value"]:
                if old_values:
                    old_values += ", "
                old_values += self.get_name(ctx.guild, ent, int_settings["type"])
        else:
            old_values = self.get_name(ctx.guild, settings["value"], int_settings["type"])
        if not old_values:
            old_values = "nothing"


        footer = int_settings["help_string"]
        regex_type = int_settings["type"]
        message = await ctx.send(f"You've decided to change the `{key_order[-1]}` "
                                 f"value that is currently `{old_values}`.\n", add_footer=footer)

        def check(m):
            return m.author == ctx.message.author
        while True:
            try:
                msg = await self.bot.wait_for("message", timeout=20, check=check)
            except asyncio.TimeoutError:
                await message.delete()
                return
            else:
                await message.delete()
                if msg.content == "cancel":
                    return
                # Get appropriate value format

                value = self.regex_filter(regex_type, msg.content, listed)
                try:
                    await msg.delete()
                except Exception:
                    pass
                if not value:
                    message = await ctx.send("You've entered a incorrect value. Try again or cancel the menu by typing `cancel`")
                else:
                    break
        steps = []
        data = ctx.server_settings
        for key in key_order:
            steps.append(data)
            data = data.get(key, None)
        counter = len(key_order)
        for key in reversed(key_order):
            counter += -1
            if counter == len(key_order)-1:
                # Working here to check if array
                steps[counter][key]["value"] = value

            else:
                steps[counter][key] = steps[counter+1]
        data = steps[0]
        values = ""
        if listed and value != "all":
            for ent in value:
                if values:
                    values += ", "
                values += self.get_name(ctx.guild, ent, int_settings["type"])
        else:
            values = self.get_name(ctx.guild, value, int_settings["type"])
        await ctx.db.execute("UPDATE settings SET settings = $1 WHERE guild_id = $2", json.dumps(data), ctx.guild.id)
        await self.bot.db.redis.set('server:{}:settings'.format(ctx.guild.id), json.dumps(data))
        await ctx.send(f"You successfully changed the value of `{old_values}` to `{values}`!")






def setup(bot):
    bot.add_cog(DashboardCog(bot))