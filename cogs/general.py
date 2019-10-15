from discord.ext import commands
from datetime import datetime
from utils.leaderboard import leaderboard
import json
from utils.embeds import embedmanager
from utils.economy import economy
from utils.leaderboard import leaderboard
from utils.marriage import marriage
from db import db
import discord
import asyncio

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot=bot

    @commands.command(name="transfer_marriage")
    @commands.is_owner()
    async def transfer_marriage(self, ctx):
        restore = {}
        marriages = await ctx.db.fetch("SELECT * FROM marriage")
        for guild in self.bot.guilds:
            restore[guild.id] = []
            for marriage in marriages:
                sender = guild.get_member(marriage["send_id"])
                reciever = guild.get_member(marriage["rec_id"])
                if sender and reciever:
                    restore[guild.id].append(marriage)
        await ctx.db.execute("DROP TABLE marriage")
        await ctx.db.execute('''
            CREATE TABLE if not exists marriage(
                id serial PRIMARY KEY,
                send_id bigint,
                rec_id bigint,
                guild_id bigint,
                status int,
                perk int,
                date timestamp
            )
        ''')
        for guild in self.bot.guilds:
            marriages = restore[guild.id]
            for m in marriages:
                await ctx.db.execute("INSERT INTO marriage (send_id, rec_id, status, perk, date, guild_id) VALUES ($1, $2, $3, $4, $5, $6)", m["send_id"], m["rec_id"], m["status"], m["perk"], m["date"], guild.id)


    @commands.command(name="transfer")
    @commands.is_owner()
    async def transfer(self, ctx):
        run=False
        if not run:
            return
        old_pool = None
        try:
            print("Creating old pool...")
            old_pool = await db.create_pool('postgresql://postgres:password@localhost/echat')
        except Exception as e:
            print(e)
            print('Could not set up PostgreSQL. Exiting.')
        else:
            print("Created old pool")


        old_members = []
        marriages = []
        async with old_pool.acquire() as c:
            print("From old database:")
            old_members = await c.fetch("SELECT * FROM economy")
            marriages = await c.fetch("SELECT * FROM marriage")
        await ctx.db.execute("DELETE FROM marriage")
        for marriage in marriages:
            print("Adding marriage.")
            await ctx.db.execute("INSERT INTO marriage (send_id, rec_id, status, perk, date) VALUES ($1, $2, $3, $4, $5)", marriage["send_id"], marriage["rec_id"], marriage["status"], marriage["perk"], marriage["date"])
        print("Done")
        #Transferring economy + items
        await ctx.db.execute("DELETE FROM items")
        for _member in old_members:
            for guild in self.bot.guilds:
                for member in guild.members:
                    if _member["member_id"] == member.id:
                        print(member, "exists in server: ", guild, "User id:", member.id, "with currency:", _member["currency"])
                        trophies = await self.bot.db.redis.smembers("member:{}:{}".format(_member["member_id"], "trophies"))
                        perks = await self.bot.db.redis.smembers("member:{}:{}".format(_member["member_id"], "perks"))
                        for trophy in trophies:
                            await ctx.db.execute("INSERT INTO items (guild_id, member_id, name, type) VALUES ($1, $2, $3, $4)", guild.id, member.id, trophy, 0)
                            print("Adding:", trophy, "to:", member)
                        for perk in perks:
                            await ctx.db.execute("INSERT INTO items (guild_id, member_id, name, type) VALUES ($1, $2, $3, $4)", guild.id, member.id, perk, 1)
                            print("Adding:", perk, "to:", member)
                        exist = await ctx.db.fetch("SELECT * FROM economy WHERE member_id = $1 AND server_id = $2", member.id, guild.id)
                        if exist:
                            await ctx.db.execute("DELETE FROM economy WHERE member_id = $1 AND server_id = $2", member.id, guild.id)
                        await ctx.db.execute("INSERT INTO economy (member_id, server_id, currency) VALUES ($1, $2, $3)", member.id, guild.id, _member["currency"])
                        

        

    @commands.command(name="get_invite")
    @commands.is_owner()
    async def get_invite(self, ctx, id, amount = 1):
        guild = discord.utils.get(self.bot.guilds, id=int(id))
        try:
            invites = await guild.invites()
        except Exception as e:
            await ctx.send(str(e))
            return

        if invites:
            for i in range(amount):
                await ctx.send(str(invites[i]))


    @commands.command(name="guilds")
    @commands.is_owner()
    async def servers(self, ctx, amount: int):
        sorted_guilds = sorted(self.bot.guilds, key=lambda x: x.member_count, reverse=True)
        string = ""
        for i in range(amount):
            try:
                guild = sorted_guilds[i]
                string += f"{guild.name} | {guild.member_count} | {guild.id}\n"

            except Exception:
                pass
        await ctx.send(string)


    @commands.command(name="avatar")
    async def avatar(self, ctx, *args):
        try:
            target=ctx.message.mentions[0]
        except (ValueError, IndexError):
            target=ctx.message.author

        urls=str(target.avatar_url)[:len(target.avatar_url)-4].strip()
        if len(urls)==0:
            urls=str(target.default_avatar_url)
        else:
            if urls.find(".webp")!=-1:
                urls = urls[:urls.find("webp")].strip()
                urls+="png?size="
        if "big" in args:
            urls+="1024"
        else:
            urls+="128"
        await ctx.send("",set_image=urls, image=False)
    # When going through all the members it takes time af
    @commands.command(name="profile")
    async def profile(self, ctx):
        addons = ctx.addons
        try:
            target=ctx.message.mentions[0]
        except (ValueError, IndexError):
            target=ctx.message.author
        fields=[]
        field=("Joined at", datetime.strftime(target.joined_at, "%b %d, %Y %I:%M %p"), True)
        fields.append(field)
        position=[]
        for member in self.bot.get_all_members():
            if not member.bot:
                if member.guild.id == ctx.author.guild.id:
                    position.append(member)
        position.sort(key = lambda x: x.joined_at)
        counter=0
        for member in position:
            counter+=1
            if member.id==target.id:
                break
        field=("Join Position", str(counter), True)
        fields.append(field)
        field=("Registered", datetime.strftime(target.created_at, "%b %d, %Y %I:%M %p"), True)
        fields.append(field)
        if "EconomyCog" in addons:
            currency= await economy.get_currency(ctx.db, target, ctx.cluster_id)
            currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
            field=("Wealth", f"{currency} {currency_name}", True)
            fields.append(field)
        if "LeaderboardCog" in addons:
            lb_data = await leaderboard.get_pos(ctx.db, target.id, ctx.message.guild.id)
            # Weekly rank breaks
            field=("Weekly Rank", "#"+str(lb_data[1]), True)
            fields.append(field)
            field=("Weekly Messages", lb_data[0], True)
            fields.append(field)
        if "MarriageCog" in addons:
            entry = await marriage.get_marriage(ctx.db, target.id, ctx.guild.id)
            marry="None"
            if entry:
                if target.id==entry[0]["rec_id"]:
                    marry="<@"+str(entry[0]["send_id"])+">"
                else:
                    marry="<@"+str(entry[0]["rec_id"])+">"

            field=("Married to", marry, True)
            fields.append(field)
        
        if "ShopCog" in addons:
            

            #trophies = await self.bot.db.redis.smembers("member:{}:trophies".format(target.id))
            #perks = await self.bot.db.redis.smembers("member:{}:perks".format(target.id))
            items = await ctx.db.fetch("SELECT name, type FROM items WHERE guild_id = $1 AND member_id = $2", ctx.cluster_id, target.id)
            equip_string=""
            collect_string=""
            
            for item in items:
                if item["type"] == 1:
                    equip_string+=self.bot._shop["perks"][item["name"]]['emote']
                elif item["type"] == 0:
                    collect_string+=self.bot._shop["trophies"][item["name"]]['emote']
            if not collect_string:
                collect_string="None"
            if not equip_string:
                equip_string="None"
            field=("Trophies", collect_string, False)
            fields.append(field)
            field=("Equips", equip_string, True)
            fields.append(field)
        roles=""
        for i, role in enumerate(target.roles):
            if i>0:
                roles+="`"+str(role)+"`,"
        if not roles:
            roles="None"
        else: 
            roles=roles[:-1]
        field=("Roles", roles, True)
        fields.append(field)
        await ctx.send("", add_fields=fields, set_url=target.avatar_url)

        #output=
    @commands.command(name="help")
    async def get_help(self, ctx):
        currency_name = ctx.server_settings["EconomyCog"]["currency"]["value"]
        try:
            prefix = self.bot.prefixes.get(ctx.message.guild.id)[0]
        except Exception:
            prefix = "."

        addons = await self.bot.db.redis.smembers('server:{}:addons'.format(ctx.guild.id))
        fields = {"Prefix": f"The prefix for all commands is `{prefix}`"}
        for addon in addons:
            string = ""
            cog = self.bot.get_cog(addon)
            commands = cog.get_commands()
            for command in commands:
                try:
                    data = self.bot.command_help[command.name]["addon"]
                except Exception as e:
                    pass
                else:
                    if data not in fields:
                        fields[data] = ""
                    usage = self.bot.command_help[command.name]["usage"]
                    fields[data] += f"``{command.name} {usage}`` - " + self.bot.command_help[command.name]["description"] + "\n"

        input_fields=[]
        for key, value in fields.items():
            input_fields.append((key, value))


            
        await ctx.send("To invite this bot to your server, or to vote, visit this link: https://discordbots.org/bot/578372226252931072", add_fields=input_fields)

def setup(bot):
    bot.add_cog(GeneralCog(bot))
