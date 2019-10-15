import discord
from discord.ext import commands
import asyncpg
import sys, traceback
import asyncio
import aiohttp
import async_timeout
from datetime import datetime, timedelta

class economy:
    @staticmethod
    async def get_currency(c, user, guild_id):
        currency = await c.fetch("SELECT currency FROM economy WHERE member_id=$1 AND server_id=$2", user.id, guild_id)
        if not currency:
            await c.execute("INSERT INTO economy (member_id, server_id, currency) VALUES ($1, $2, $3)", user.id, guild_id,0)
            return 0
        return currency[0]['currency']
    @staticmethod
    async def update_currency(c, user, guild_id, add):
        # A single query that tries to add a user to the table. If the user already exists, it instead updates the current entry.
        result = await c.execute("UPDATE economy SET currency = currency+$2 WHERE member_id = $1 AND server_id = $3", user.id, add, guild_id)
        if str(result) == "UPDATE 0":
            await c.execute("INSERT INTO economy (member_id, server_id, currency) VALUES ($1, $2, $3)", user.id, guild_id, add)

    @staticmethod
    async def get_cooldown(c, user, guild_id, mode):
        date = await c.fetch("SELECT date FROM cooldowns WHERE member_id=$1 AND server_id=$3 AND mode=$2", user.id, mode, guild_id)
        return date
    #Send in current date + time of cooldown
    @staticmethod 
    async def update_cooldown(c, user, guild_id, cooldown, mode):
        date=datetime.now()+timedelta(hours=cooldown)
        # Temporary during testing
        #date=datetime.now()+timedelta(seconds=10)
        await c.execute("UPDATE cooldowns SET date=$1 WHERE member_id=$2 AND server_id=$4 AND mode=$3",date, user.id, mode, guild_id)
    @staticmethod
    async def create_cooldown(c, user, guild_id, cooldown, mode):
        date=datetime.now()+timedelta(hours=cooldown)
        #date=datetime.now()+timedelta(seconds=10)
        await c.execute("INSERT INTO cooldowns (member_id, server_id, date, mode) VALUES ($1, $2, $3, $4)", user.id, guild_id,date, mode)
    @staticmethod
    async def get_top(c, guild_id, limit):
        lb_data = await c.fetch("SELECT currency, member_id FROM economy WHERE server_id=$1 ORDER BY currency DESC LIMIT $2", guild_id, limit)
        return lb_data
