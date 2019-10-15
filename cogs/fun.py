import discord
from discord.ext import commands
import os
import random
from discord import TextChannel


class FunCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.whip_images = ["https://cdn.discordapp.com/attachments/460111213649461248/461643645985095690/whip2.gif", "https://cdn.discordapp.com/attachments/366335793658331137/461641836856082432/whip1.gif", "https://cdn.discordapp.com/attachments/460111213649461248/461643739677458454/whip6.gif", "https://cdn.discordapp.com/attachments/460111213649461248/461643930987921409/whip4.gif", "https://cdn.discordapp.com/attachments/460111213649461248/461643973937856522/whip3.gif", "https://cdn.discordapp.com/attachments/460111213649461248/461644021454864384/whip5.gif", "https://cdn.discordapp.com/attachments/460111213649461248/461644224396525569/whip10.gif", "https://cdn.discordapp.com/attachments/460111213649461248/461644305245667339/whip8.gif", "https://cdn.discordapp.com/attachments/460111213649461248/461644476641837067/whip9.gif", "https://cdn.discordapp.com/attachments/460111213649461248/461644603066548225/whip7.gif"]
        self.bam_images = ["https://cdn.discordapp.com/attachments/480798534409650186/509420445980819467/giphy_2.gif", "https://cdn.discordapp.com/attachments/480798534409650186/509420392558100501/giphy_3.gif", "https://cdn.discordapp.com/attachments/480798534409650186/509420341202780196/giphy_4.gif", "https://cdn.discordapp.com/attachments/480798534409650186/509420304708272159/giphy.gif", "https://cdn.discordapp.com/attachments/480798534409650186/509420229823037460/O3DHIA5.gif", "https://cdn.discordapp.com/attachments/480798534409650186/509420143839936522/azCR8D1.gif"]

    @commands.command()
    async def whip(self, ctx, target: discord.Member):
        whip_image = random.choice(self.whip_images)
        await ctx.send("You whipped the shit out of "+target.name, set_image=whip_image, image=False)

    @commands.command()
    async def bam(self, ctx, target: discord.Member):
        bam_image = random.choice(self.bam_images)
        await ctx.send(f"You bammed the shit out of {target.name}", set_image=bam_image, image=False)

    @commands.command()
    async def set_channel(self, ctx, channel_id):
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            self.channel = channel
            await ctx.send("Setting the channel succeeded")
        else:
            await ctx.send("Setting the channel failed")

    @commands.command()
    async def speak(self, ctx):
        message = ctx.message.content.split(".speak ")
        message = message[1]
        if self.channel:
            await self.channel.send(message)
            await ctx.message.delete()
        else:
            await ctx.send("No channel set")

    async def get_user_reaction(self, ctx, message, reactions):

        reaction, user = await self.bot.wait_for('reaction_add',)


    @commands.Cog.listener("on_raw_reaction_add")
    async def on_reaction_add(self, payload):
        reactions = ["⚪", "⚫"]
        # YIN                                  #YANG
        role_ids = [611866314738368521, 611866869778874369]

        # The annoucement message id
        message_id = 611933810837422091
        # This means the reaction was done to the selected message
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)

        # Check if the member has one of the roles already
        for role in member.roles:
            if role.id in role_ids:
                return

        if payload.message_id == message_id:
            # If the reaction is one of the selected:
            print(payload.emoji)
            emoji = str(payload.emoji)
            if emoji in reactions:
                #White / Yang
                if emoji == "⚪":
                    role = guild.get_role(611866869778874369)
                    await self.assign_role(member, role)
                #black / Yin
                elif emoji == "⚫":
                    role = guild.get_role(611866314738368521)
                    await self.assign_role(member, role)

    async def assign_role(self, member, role):
        if member.bot:
            return
        print("Assign:", role, "to:", member)
        await member.add_roles(role)


def setup(bot):
    bot.add_cog(FunCog(bot))
