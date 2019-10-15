import asyncpg
import asyncio

def with_connection(f):
    def with_connection_(*args, **kwargs):
        # or use a pool, or a factory function...
        cnn = psycopg.connect(DSN)
        try:
            rv = await f(cnn, *args, **kwargs)
        except Exception, e:
            cnn.rollback()
            raise
        else:
            cnn.commit() # or maybe not
        finally:
            cnn.close()

        return rv

    return with_connection_

async def get_command_settings(cursor, name, guild_id):
  await cursor.fetch("SELECT embed_settings, command_settings FROM commands WHERE server_id=$1 AND command_name=$2", message.guild.id, ctx.command.name)
