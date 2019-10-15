import discord
from discord.ext import commands
import asyncpg
import sys, traceback
import asyncio
import aiohttp
import async_timeout
from datetime import datetime, timedelta

class marriage:
    async def send_request(c, send_id, rec_id, guild_id):
        check = await c.fetch("SELECT * FROM marriage WHERE guild_id = $3 AND (status=1 AND ((rec_id=$1 OR send_id=$1) OR (rec_id=$2 OR send_id=$2)) OR ((rec_id=$1 AND send_id=$2) OR (rec_id=$2 AND send_id=$1)))", send_id, rec_id, guild_id)
        if check:
            return check[0]
        await c.execute("INSERT INTO marriage (send_id, rec_id, status, perk, guild_id) VALUES ($1, $2, $3, $4, $5)", send_id, rec_id, 0, 0, guild_id)
        return check

    async def accept_request(c, user_id, send_id, guild_id):
        date=datetime.now()
        result=await c.execute("UPDATE marriage SET status=$4, date=$5 WHERE rec_id=$1 AND send_id=$2 AND status=$3 AND guild_id = $6", user_id, send_id, 0, 1, date, guild_id)
        if '1' in str(result):
            return True
        return False
    async def decline_request(c, user_id, send_id, guild_id):
        result = await c.execute("DELETE FROM marriage WHERE rec_id=$1 AND send_id=$2 AND status=$3 AND guild_id = $4", user_id, send_id, 0, guild_id)
        if '1' in str(result):
            return True
        return False
    async def remove_request(c, user_id, status, guild_id):
        result = await c.execute("DELETE FROM marriage WHERE (rec_id=$1 OR send_id=$1) AND status=$2 AND guild_id = $3", user_id, status, guild_id)
        if '1' in str(result):
            return True
        return False
    async def get_marriage(c, user_id, guild_id):
        result = await c.fetch("SELECT * FROM marriage WHERE status=$1 AND (rec_id=$2 OR send_id=$2) AND guild_id = $3", 1, user_id, guild_id)
        return result