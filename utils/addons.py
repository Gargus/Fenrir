import discord
from discord.ext import commands
import asyncpg
import sys, traceback
import asyncio
import aiohttp
import async_timeout
import datetime
import time
# Retrieves the addons from the database, and returns them 
# [Generator]
def timer(func):
    async def func_wrapper(*args, **kwargs):
        start=time.time()
        result = await func(*args, **kwargs)
        print(time.time()-start)
        return result
    return func_wrapper

#@timer
async def get_active_addons(cursor, server):
    addons = await cursor.fetch("SELECT addon_name, addon_settings FROM addons WHERE server_id=$1", server)
    addon_name=[]
    addon_setting=[]  # alla namn | alla settings  (list[namn], list[settings])
    for addon in addons:
        addon_name.append(addon[0])
        addon_setting.append(addon[1])
    return (addon_name, addon_setting)

    
#@timer
async def get_active_addons2(cursor, server):
    addons = await cursor.fetch("SELECT addon_name, addon_settings FROM addons WHERE server_id=$1", server)
    return addons