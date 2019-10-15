from discord.ext import commands
from datetime import datetime, timedelta
from utils.economy import economy
import utils.checks as checks
import random
import asyncio
import time


class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tasks = {"work": {}}

    async def main_setup(self):
        await self.setup_auto()

    async def auto_work(self, user):
        while True:
            async with self.bot.pool.acquire() as c:
                cooldowned = 4
                acquire_range = (350, 500)
                coins = random.randint(acquire_range[0], acquire_range[1])
                perks_unsorted = await c.fetch("SELECT name FROM items WHERE "
                                               "guild_id = $1 AND member_id = $2 AND type = $3"
                                               , user.guild.id, user.id, 1)
                perks = [x["name"] for x in perks_unsorted]

                if perks:
                    for perk in perks:
                        if perk == "Hourglass":
                            cooldowned = 1
                        if perk == "Degree":
                            coins = coins*2

                minutes = cooldowned * 60
                seconds = minutes * 60
                cooldown = await economy.get_cooldown(c, user, user.guild.id, "work")
                if not cooldown:
                    await economy.update_currency(c, user, user.guild.id, coins)  # Updates the currency
                    await economy.create_cooldown(c, user, user.guild.id, cooldowned, "work")  # Updates the cooldown
                    timer=seconds+10
                else:
                    delta = cooldown[0]["date"]-datetime.now()
                    compare = timedelta(0)
                    if delta < compare:
                        # Run stuff
                        await economy.update_currency(c, user, user.guild.id, coins) # Updates the currency
                        await economy.update_cooldown(c, user, user.guild.id, cooldowned, "work")  # Updates the cooldown
                        timer = seconds+10
                        
                    else:
                        # Now it will wait as long as it takes until work can be done again
                        timer = delta.seconds+10
            await asyncio.sleep(timer)

    async def setup_auto(self):
        cog = self.bot.get_cog("DonorCog")

        # Members that should be checked
        donors = cog.get_all_donor_members()
        for donor in donors:
            if donor.id not in self.tasks["work"]:
                self.tasks["work"][donor.id] = {}
            task_status = await self.bot.db.redis.get(f"member:{donor.id}:guild:{donor.guild.id}:work_task")
            if task_status:
                task = self.bot.loop.create_task(self.auto_work(donor))
                self.tasks["work"][donor.id][donor.guild.id] = task

    @commands.command(name="autowork")
    @commands.check(checks.check_if_donor)
    async def autowork(self, ctx):
        if ctx.donor["permission"] < 2:
            raise commands.CheckFailure("donor")
        # Should start or kill task depending if it exists or not
        if ctx.author.id not in self.tasks["work"]:
            self.tasks["work"][ctx.author.id] = {}
        task = self.tasks["work"][ctx.author.id].get(ctx.guild.id, None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        else:
            task = ctx.bot.loop.create_task(self.auto_work(ctx.author))
            self.tasks["work"][ctx.author.id][ctx.guild.id] = task
            await self.bot.db.redis.set(f"member:{ctx.author.id}:guild:{ctx.guild.id}:work_task", 1)
            await ctx.db.execute("UPDATE donors SET aw_guild_id = array_append(aw_guild_id, $1) WHERE member_id = $2", ctx.guild.id, ctx.author.id)
            await ctx.send("You've successfully enabled your Auto-Work service!")
            
            return

        if task.cancelled():
            await ctx.db.execute("UPDATE donors SET aw_guild_id = array_remove(aw_guild_id, $1) WHERE member_id = $2", ctx.guild.id, ctx.author.id)
            await self.bot.db.redis.delete(f"member:{ctx.author.id}:guild:{ctx.guild.id}:work_task")
            del self.tasks["work"][ctx.author.id][ctx.guild.id]
            await ctx.send("You've successfully cancelled your Auto-Work service!")
        else:
            await ctx.send("The cancellation failed. Report this to Hampe#6969 <@465976233251962900> so that stupid goon can fix the issue")
            raise commands.CommandInvokeError("Failed to end task")

    @commands.command(name="steal")
    async def steal(self, ctx):
        try:
            target=ctx.message.mentions[0]
        except (ValueError, IndexError):
            raise commands.BadArgument
        if target.bot:
            await ctx.send("You can't steal from bots", image=False)
            return
        if target == ctx.message.author:
            await ctx.send("You can't steal from yourself", image=False)
            return
        cooldown=4
        acquire_range=(50,500)
        coins=random.randint(acquire_range[0], acquire_range[1])
        if ctx.perks:
            for perk in ctx.perks:
                if perk == "Hourglass":
                    cooldown=1
                if perk == "Incognito":
                    coins=coins*2

        # change this in case of clusters
        guild_id = ctx.author.guild.id

        currency = await economy.get_currency(ctx.db, ctx.message.author, guild_id)
        date = await economy.get_cooldown(ctx.db, ctx.message.author, guild_id, "steal")
        if not date:
            cog = self.bot.get_cog("DonorCog")
            donor = cog.get_user(target.id)
            if donor:
                coins = round(coins / (1 + (donor["permission"])))
            await economy.update_currency(ctx.db, ctx.message.author, guild_id, coins)
            await economy.update_currency(ctx.db, target, guild_id, -coins)
            await economy.create_cooldown(ctx.db, ctx.message.author, guild_id, cooldown, "steal")
        else:
            date=date[0]['date']
            if datetime.today()>date:
                cog = self.bot.get_cog("DonorCog")
                donor = cog.get_user(target.id)
                if donor:
                    coins = round(coins / (1 + (donor["permission"])))
                await economy.update_currency(ctx.db, ctx.message.author, guild_id, coins)
                await economy.update_currency(ctx.db, target, guild_id, -coins)
                await economy.update_cooldown(ctx.db, ctx.message.author, guild_id, cooldown, "steal")
            else:
                output=str(date-datetime.now())
                output=output[:output.find(".")].strip()
                await ctx.send(f"You need some rest! You can steal again in {output} hours.", image=False)
                return

        #embed this
        currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
        string=f"You stole `{coins}` {currency_name} from {target.name} {target.mention}." \
               f"\nYour new balance is `{currency+coins}` {currency_name}."
        await ctx.send(string)

    @commands.command(name="work")
    async def work(self, ctx):
        start = time.time()
        cooldown=4
        acquire_range=(350, 500)
        coins=random.randint(acquire_range[0], acquire_range[1])
        if ctx.perks:
            for perk in ctx.perks:
                if perk == "Hourglass":
                    cooldown=1
                if perk == "Degree":
                    coins=coins*2

        currency = await economy.get_currency(ctx.db, ctx.message.author, ctx.cluster_id)
        date = await economy.get_cooldown(ctx.db, ctx.message.author, ctx.cluster_id, "work") #Getting the cooldown / Checks if any entry exists
        if not date:
            await economy.update_currency(ctx.db, ctx.message.author, ctx.cluster_id, coins) #Updates the currency
            await economy.create_cooldown(ctx.db, ctx.message.author, ctx.cluster_id, cooldown, "work") #Updates the cooldown
        else:
            date=date[0]['date']
            if datetime.today()>date:
                await economy.update_currency(ctx.db, ctx.message.author, ctx.cluster_id, coins) #Updates the currency
                await economy.update_cooldown(ctx.db, ctx.message.author, ctx.cluster_id, cooldown, "work") #Updates the cooldown
            else:
                output=str(date-datetime.now())
                output=output[:output.find(".")].strip()
                await ctx.send(f"You need some rest! You can work again in {output} hours.", image=False)
                return
        currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
        await ctx.send(f"You worked for a few hours and earned `{coins}` {currency_name}.\nYour new balance is `{currency+coins}` {currency_name}.")

    @commands.command(name="convert")
    async def convert(self, ctx):

        guild_id = ctx.author.guild.id

        compare = await ctx.db.fetch("SELECT value from convert WHERE member_id = $1 and guild_id = $2", ctx.author.id, ctx.cluster_id)
        if not compare:
            await ctx.db.execute("INSERT INTO convert (member_id, guild_id, value) VALUES ($1, $2, $3)", ctx.author.id, ctx.cluster_id, 0)
            compare = 0
        else:
            #possibly error
            try:
                compare = compare[0]["value"]
            except (ValueError, IndexError):
                return
        current = await ctx.db.fetch("SELECT value from leaderboard WHERE member_id = $1 and server_id = $2", ctx.author.id, ctx.cluster_id)
        # possibly error
        if not current:
            await ctx.send("You don't have any messages registered to the leaderboard to convert", image=False)
            return
        current = current[0]["value"]
        acquire = messages = int(current) - compare
        multiplier = 1
        if ctx.perks:
            for perk in ctx.perks:  
                if perk == "Keycard":
                    multiplier += 1
                if perk == "Bank":
                    multiplier += 1
                if perk == "Arbitrage":
                    multiplier += 1
        acquire = acquire * multiplier
        currency = await economy.get_currency(ctx.db, ctx.author, ctx.cluster_id)
        await economy.update_currency(ctx.db, ctx.author, ctx.cluster_id, acquire)
        await ctx.db.execute("UPDATE convert SET value = $1 WHERE member_id = $2 and guild_id = $3", int(current), ctx.author.id, ctx.cluster_id)
        currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
        await ctx.send(f"Converted `{messages}` messages to `{acquire}` {currency_name}.\nYour new balance is `{int(currency+acquire)}` {currency_name}")

    @commands.command(name="bank")
    async def bank(self, ctx):
        string=""
        try:
            user=ctx.message.mentions[0]
            string+=user.name+" has "
        except (ValueError, IndexError):
            user=ctx.message.author
            string+="You have "
        finally:
            currency = await economy.get_currency(ctx.db, user, ctx.cluster_id)

            #embed this
            currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
            await ctx.send(string+f"`{currency}` {currency_name}.")

    @commands.command(name="bet")
    async def coinflip(self, ctx, choice: str, amount: int):
        heads = ["heads", "h"]
        tails = ["tails", "t"]
        if amount < 1:
            raise commands.BadArgument
        value = amount
        if choice in heads:
            pickvar=1
        elif choice in tails:
            pickvar=0
        else:
            await ctx.send("That option does not exist. These are the existing alternatives:", add_fields=[("Heads", heads), ("Tails", tails)])
            return


        currency= await economy.get_currency(ctx.db, ctx.message.author, ctx.cluster_id)
        currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
        if not currency>=value:
            await ctx.send("You don't have enough {}".format(currency_name))
            return
        string=""
        rng=random.SystemRandom()
        randvar=rng.randint(0, 1)

        if randvar==1:
            string+="You landed on Heads\n"
        else:
            string+="You landed on Tails\n"
        if randvar==pickvar: #Win
            await economy.update_currency(ctx.db, ctx.message.author, ctx.cluster_id, value)
            string+=f"You won `{value}` {currency_name}.\nYour new balance `{currency+value}` {currency_name}."
        else: #Lose
            await economy.update_currency(ctx.db, ctx.message.author, ctx.cluster_id, -value)
            string+=f"You lost `{value}` {currency_name}.\nYour new balance `{currency-value}` {currency_name}."
        await ctx.send(string)
         
    @commands.command(name="eco")
    async def economy_rank(self, ctx):
        data = await economy.get_top(ctx.db, ctx.cluster_id, 20)
        string=""
        currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
        i = 0
        for entry in data:
            user=ctx.guild.get_member(entry['member_id'])
            currency=str(entry['currency'])
            if user:
                string+=f'**{i+1}. {user.name} {user.mention}: {currency} {currency_name}**\n'
                i +=1
            if i == 10:
                break

        title="Currency"
        await ctx.send(string, title="{} Leaderboard".format(title))

    @commands.command(name="gift")
    async def gift(self, ctx, user, amount: int):
        if amount<1:
            raise commands.BadArgument
        try:
            target=ctx.message.mentions[0]
        except (ValueError, IndexError):
            await ctx.send("You have to tag someone to use this command", image=False)
            return
        if target == ctx.author:
            await ctx.send("You can't gift yourself.", image=False)
            return


        currency = await economy.get_currency(ctx.db, ctx.message.author, ctx.cluster_id)
        currency_name=ctx.server_settings["EconomyCog"]["currency"]["value"]
        if currency<amount:
            await ctx.send("You don't have enough {}".format(currency_name))
            return
        await economy.update_currency(ctx.db, target, ctx.cluster_id, amount)
        await economy.update_currency(ctx.db, ctx.message.author, ctx.cluster_id, -amount)
        await ctx.send(f"You gifted {target.name} {target.mention} `{str(amount)}` {currency_name}")

    @commands.command(name="simulate")
    async def simulate(self, ctx):
        rng = random.SystemRandom()


        # Lets say this is tails
        pick = 0

        # The bank
        bank = 5000


        static_bet = 100
        # How much we should be betting
        bet = static_bet

        rounds = 0
        lose_c = 0
        median = 0
        #for fuck in range(100):
        for _ in range(100000):
            rounds+=1
            if bank <= 0:
                break
            if bank > 0 and bank < 10000:
                median += 1
            if lose_c >= 4:
                bet = static_bet


            # This will be either 0 or 1
            randvar = rng.randint(0, 1)

            # This means we won the bet
            if randvar == pick:
                lose_c = 0

                #Since we won, the add the "bet" amount to the bank
                bank = bank+bet

                #And now we can reset it back to 100
                bet = static_bet

            # This means we lost
            else:
                lose_c += 1
                #If we lose,  remove the lost bet from the bank
                bank = bank-bet

                #But also increase the "bet" value to twice as much
                #If it was 200, it is now 400
                bet = bet+bet

        print("Rounds:", rounds)
        print("Bank:", bank)
        print("Median:", median)




    
def setup(bot):
    bot.add_cog(EconomyCog(bot))