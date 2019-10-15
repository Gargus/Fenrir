import discord
from discord.ext import commands
import asyncpg
import sys, traceback
import asyncio
import aiohttp
import async_timeout
import datetime


async def global_adder(c, server_id):
    # Experimental global adder
    data = await c.fetch("SELECT guild_id, value FROM global_leaderboard WHERE guild_id=$1", server_id)
    if data:
        await c.execute("UPDATE global_leaderboard SET value=$1 WHERE guild_id=$2", data[0]["value"] + 1, server_id)
    else:
        await c.execute("INSERT INTO global_leaderboard (guild_id, value) VALUES ($1, $2)", server_id, 1)
    #


class leaderboard:
    @staticmethod
    async def adder(c, message, cog):

        # Anti "Spam" filter advanced.
        # Removes messages if it has been mentioned multiple times within 1 minute

        history = cog.history.get(message.author.id, None)
        delta = datetime.timedelta(minutes=1)
        if not history:
            # Append both the message and the current time
            cog.history[message.author.id] = []
            cog.history[message.author.id].append((message.content, datetime.datetime.now() + delta))
        else:
            for i, (msg, timed) in enumerate(history):
                now = datetime.datetime.now()

                # If now is smaller than timed, we need to check the message (within 1 minute)
                if now < timed:

                    # If the message is the same, we do not count it, aka returning
                    if message.content == msg:
                        # Replaces the time of the same location in the list
                        cog.history[message.author.id][i] = (message.content, datetime.datetime.now() + delta)
                        return
                    # If the just typed message starts with another added message (aka a dublicate with potential)
                    # added content
                    elif message.content.startswith(msg):
                        cog.history[message.author.id][i] = (message.content, datetime.datetime.now() + delta)
                        return

                # A timer has reached above 1 minute, and entry shall then be removed
                else:
                    del cog.history[message.author.id][i]

            # Add this message to the history
            cog.history[message.author.id].append((message.content, datetime.datetime.now() + delta))


        # check for cluster
        cluster = await c.fetchrow("SELECT cluster_id FROM cluster WHERE guild_id = $1", message.guild.id)
        guild_id = message.guild.id
        if cluster:
            guild_id = cluster["cluster_id"]


        lb_data = await c.fetch("SELECT date, value FROM leaderboard WHERE server_id=$1 AND member_id=$2", guild_id, message.author.id)
        cooldown=3
        date=datetime.datetime.now()+datetime.timedelta(seconds=cooldown)
        if lb_data:
            if lb_data[0]['date']<datetime.datetime.now():
                await global_adder(c, message.guild.id)

                await c.execute("UPDATE leaderboard SET value=$1, date=$2 WHERE member_id=$3 AND server_id=$4", lb_data[0]["value"]+1 , date, message.author.id, guild_id)
        else:
            await global_adder(c, message.guild.id)
            await c.execute("INSERT INTO leaderboard (server_id, member_id, value, date) VALUES ($1, $2, $3, $4)", guild_id, message.author.id, 1, date)
    @staticmethod
    async def global_adder(c, server_id):
        data = await c.fetch("SELECT guild_id, value FROM global_leaderboard WHERE guild_id=$1", server_id)
        if data:
            await c.execute("UPDATE global_leaderboard SET value=$1 WHERE guild_id=$2", data[0]["value"]+1, server_id)
        else:
            await c.execute("INSERT INTO global_leaderboard (guild_id, value) VALUES ($1, $2)", server_id, 1)
    @staticmethod
    async def get_top(c, limit, server_id):
        if limit <= 10 and limit >=1:
            if server_id:
                lb_data = await c.fetch("SELECT value, member_id, server_id FROM leaderboard WHERE server_id=$1 ORDER BY value DESC LIMIT $2", server_id, limit)
            else:
                lb_data = await c.fetch("SELECT value, guild_id FROM global_leaderboard ORDER BY value DESC LIMIT $1", limit)
                
            return lb_data
        else:
            return
    @staticmethod
    async def get_pos(c, user_id, server_id=None):
        while True:
            if server_id:
                data = await c.fetch("SELECT value, member_id FROM leaderboard WHERE server_id=$1 ORDER BY value DESC", server_id)
            else:
                data = await c.fetch("SELECT value, member_id FROM global_leaderboard ORDER BY value DESC")

            for i, row in enumerate(data):
                if user_id==row['member_id']:
                    return (row['value'], i+1)
            date = datetime.datetime.now()
            if server_id:
                await c.execute("INSERT INTO leaderboard (server_id, member_id, value, date) VALUES ($1, $2, $3, $4)", server_id, user_id, 1, date)
            else:
                await c.execute("INSERT INTO global_leaderboard (member_id, value, date) VALUES ($1, $2, $3)", user_id, 1, date)
        
    @staticmethod
    async def get_member(c, position, server_id=None):
        if server_id:
            data = await c.fetch("SELECT value, member_id, server_id FROM leaderboard WHERE server_id=$1 ORDER BY value DESC", server_id)
        else:
            data = await c.fetch("SELECT value, member_id FROM global_leaderboard ORDER BY value DESC")
        try:
            payload=data[position-1]['value'], data[position-1]['member_id']
        except (ValueError, IndexError):
            return []
        return payload

            


        
