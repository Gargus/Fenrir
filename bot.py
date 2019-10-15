import discord
import asyncio
import config
import asyncpg
from thor import Thor
from db import db

table_queries=[
            '''
            CREATE TABLE if not exists leaderboard(
                id serial PRIMARY KEY,
                server_id bigint,
                member_id bigint,
                value int,
                date timestamp
            )
        ''',
            '''
            CREATE TABLE if not exists economy(
                id serial PRIMARY KEY,
                member_id bigint,
                server_id bigint,
                currency bigint
            )
        ''',
            '''
            CREATE TABLE if not exists cooldowns(
                id serial PRIMARY KEY,
                member_id bigint,
                server_id bigint,
                date timestamp,
                mode text
            )
        ''',
            '''
            CREATE TABLE if not exists marriage(
                id serial PRIMARY KEY,
                send_id bigint,
                rec_id bigint,
                status int,
                guild_id bigint,
                perk int,
                date timestamp
            )
        ''',
            '''
            CREATE TABLE if not exists RESET(
                id serial PRIMARY KEY,
                guild_id bigint,
                date timestamp
            )
        ''',
            '''
            CREATE TABLE if not exists convert(
                id serial PRIMARY KEY,
                guild_id bigint,
                member_id bigint,
                value int
            )
        ''',
            '''
            CREATE TABLE if not exists global_leaderboard(
                id serial PRIMARY KEY,
                guild_id bigint,
                value int
            )
        ''',
            '''
            CREATE TABLE if not exists items(
                id serial PRIMARY KEY,
                guild_id bigint,
                member_id bigint,
                name text,
                type int
            )
        ''',
            '''
            CREATE TABLE if not exists votes(
                id serial PRIMARY KEY,
                member_id bigint,
                date timestamp
            )
        ''',
            '''
            CREATE TABLE if not exists shop(
                id serial PRIMARY KEY,
                guild_id bigint,
                name text,
                description text,
                emote text,
                price bigint,
                type int,
                effect json
            )
        ''',
            '''
            CREATE TABLE if not exists automod(
                id serial PRIMARY KEY,
                guild_id bigint,
                feature text,
                channel_id text[]
            )
            
        ''',
            '''
            CREATE TABLE if not exists addons(
                id serial PRIMARY KEY,
                guild_id bigint,
                addons text[]
            )
        ''',
            '''
            CREATE TABLE if not exists settings(
                id serial PRIMARY KEY,
                guild_id bigint,
                settings json,
                size int
            )
        ''',
            '''
            CREATE TABLE if not exists donors(
                id serial PRIMARY KEY,
                member_id bigint,
                quote text,
                aw_guild_id bigint[]
            )
        ''',
            '''
            CREATE TABLE if not exists prefix(
                id serial PRIMARY KEY,
                guild_id bigint,
                prefix text
            )
        ''',
            '''
            CREATE TABLE if not exists player(
                id serial PRIMARY KEY,
                user_id bigint,
                xp bigint,
                health bigint,
                skill int,
                strength int
            )
        ''',
            '''
            CREATE TABLE if not exists equips(
                id serial PRIMARY KEY,
                rarity smallint,
                owner_id bigint,
                position text,
                type text,
                fp text
            )
            
        ''',
            '''
            CREATE TABLE if not exists cluster(
                id serial PRIMARY KEY,
                guild_id bigint,
                cluster_id bigint,
                name text
            )
        
        '''
        ]


def db_setup():
    run = asyncio.get_event_loop().run_until_complete
    try:
        print("Setting up tables...")
        for query in table_queries:
            run(db.create_table(config.postgresql, query))
    except Exception as e:
        print(e)
        print('Could not set up PostgreSQL. Exiting.')
        return
    print("Table setup done")


def run_bot():

    loop = asyncio.get_event_loop()
    try:
        print("Creating pool...")
        pool = loop.run_until_complete(db.create_pool(config.postgresql))
    except Exception as e:
        print('Could not set up PostgreSQL. Exiting.')

    bot = Thor()
    bot.pool= pool

    # The guild id for the support server
    bot.home_guild_id = 472546414455685132
    bot.run(config.bot_token)


db_setup()
run_bot()
