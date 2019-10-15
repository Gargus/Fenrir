import asyncio
import math
import aioredis
import time
import json
from datetime import timedelta
import asyncio

def weekstart(today):
    weekday=int(today.weekday())
    hour=int(today.hour)
    minute=int(today.minute)
    second=int(today.second)
    data=today-timedelta(days=weekday, hours=hour, minutes=minute, seconds=second)+timedelta(days=7)
    return data

async def result_output(cur, server_id=None):
    if server_id:
        lb_data = await cur.fetch("SELECT value, member_id, server_id FROM leaderboard WHERE server_id=$1 ORDER BY value DESC LIMIT $2", server_id, 10)
    else:
        lb_data = await cur.fetch("SELECT value, guild_id FROM global_leaderboard ORDER BY value DESC LIMIT $1", 10)
    return lb_data
