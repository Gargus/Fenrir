from discord.ext import commands
import json
import asyncio
import utils.checks as checks
import re

class DonorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.donor_roles = []
        self.donors = {}
        self.themes = {}
        self.theme_list = []

    async def main_setup(self):
        await self.setup_donors()




    async def assign(self, user_id, permission):
        self.donors[user_id] = {"permission": permission, "theme": self.themes[self.theme_list[permission]]}
        async with self.bot.pool.acquire() as c:
            check = await c.fetch("SELECT * FROM donors WHERE member_id = $1", user_id)
            if not check:
                await c.execute("INSERT INTO donors (member_id, quote, aw_guild_id) VALUES ($1, $2, $3)", user_id , None, [])
        print("Added permission level:", permission, "to:", user_id)

    async def remove(self, user_id):
        # Removes from donor list
        del self.donors[user_id]
        # Removes donor from db
        async with self.bot.pool.acquire() as c:
            await c.execute("DELETE FROM donors WHERE member_id = $1", user_id)
        # Removes autonomous tasks
        cog = self.bot.get_cog("EconomyCog")
        tasks = cog.tasks["work"].get(user_id, None)
        if tasks:
            for guild_id in tasks.keys():

                await self.bot.db.redis.delete("member:{}:guild:{}:work_task".format(user_id, guild_id))
                task = tasks.get(guild_id)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del cog.tasks["work"][user_id]

            
    def get_donor_roles(self):
        return self.donor_roles

    def get_user(self, user_id):
        return self.donors.get(user_id, None)

    def get_all_donors(self):
        return self.donors

    def get_all_donor_ids(self):
        return self.donors.keys()

    def get_all_donor_members(self):
        members = []
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.id in self.donors.keys():
                    members.append(member)
        return members

    async def setup_donors(self):

        with open("themes.json") as f:
            self.themes = json.load(f)

        donor_ids = [507336053158445092, 507324154383433738, 507336193546125333, 507369940676902932, 507381388832669696, 507373034001399809]
        self.theme_list = ["blue", "gold", "green", "purple", "redish", "red"]
        guild = self.bot.get_guild(self.bot.home_guild_id)
        async with self.bot.pool.acquire() as c:
            for i, donor_id in enumerate(donor_ids):
                role = guild.get_role(donor_id)
                for member in role.members:
                    self.donors[member.id] = {"permission": i, "theme": self.themes[self.theme_list[i]]}
                    check = await c.fetch("SELECT * FROM donors WHERE member_id = $1", member.id)
                    if not check:
                        await c.execute("INSERT INTO donors (member_id, quote, aw_guild_id) VALUES ($1, $2, $3)", member.id, None, [])

                self.donor_roles.append(role)

    @commands.command(name="theme")
    async def theme(self, ctx):
        donor = self.donors.get(ctx.author.id, None)
        options = ["black"]
        string="``black``\n"
        if donor:
            for i in range(donor["permission"]+1):
                theme = self.theme_list[i]
                string += f"``{theme}``\n"
                options.append(theme)
        msg = await ctx.send("Select the type of theme you want to use", add_fields=[("Themes:", string)])

        def check(m):
            if m.content in options:
                return m.author == ctx.message.author
        try:
            message = await self.bot.wait_for('message', timeout=20, check=check)
        except asyncio.TimeoutError:
            await msg.delete()
        else:
            if donor:
                self.donors[ctx.author.id] = {"permission": donor["permission"], "theme": self.themes[message.content]}
            await msg.delete()
            await message.delete()
            await ctx.send(f"You've successfully changed your theme to {message.content}!")

    @commands.command()
    @commands.check(checks.check_if_donor)
    async def quote(self, ctx):
        quote = await self.bot.db.redis.get(f"member:{ctx.author.id}:quote")
        msg = await ctx.send("Thanks for being a patron and supporting in the development of this bot!\n\n "
                             "Here you get so insert your own quote, which will then be displayed in the"
                             " website Hall of Fame!\n\n If it's deemed inappropriate (racism, sexism, link etc), "
                             "it will be removed.\n",
                             add_footer="Type the text that you'd like to add as a quote (max 150 characters)."
                                        " You can change it by "
                                        "using the command again.",
                             add_fields=[("Current quote", quote)])

        def check(m):
            if len(m.content) > 150:
                return False
            pattern = r"(http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)"
            val = re.match(pattern, m.content)
            if val is None:
                return m.author == ctx.message.author

        try:
            message = await self.bot.wait_for('message', timeout=60, check=check)
        except asyncio.TimeoutError:
            await msg.delete()
        else:
            await ctx.db.execute("UPDATE donors SET quote = $1 WHERE member_id = $2", message.content, ctx.author.id)
            await self.bot.db.redis.set('member:{}:quote'.format(ctx.author.id), message.content)
            await ctx.send("You successfully updated your quote! To watch it live, go to:\nhttps://www.fenrirbot.com/halloffame")



            
        



def setup(bot):
    bot.add_cog(DonorCog(bot))