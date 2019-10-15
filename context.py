from discord.ext import commands
from utils.embeds import embedmanager
import time

class _ContextDBAcquire:
    __slots__ = ('ctx', 'timeout')

    def __init__(self, ctx, timeout):
        self.ctx = ctx
        self.timeout = timeout

    def __await__(self):
        return self.ctx._acquire(self.timeout).__await__()

    async def __aenter__(self):
        await self.ctx._acquire(self.timeout)
        return self.ctx.db

    async def __aexit__(self, *args):
        await self.ctx.release()

class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = self.bot.pool
        self.db = None
        self.perms = {}
        self.cluster_id = self.guild.id

    async def send(self, *args, **kwargs):
        if kwargs.get('file'):
            string = ""
            if args[0]:
                string = args[0]
            return await super().send(string, file=kwargs.get('file'))
        title = kwargs.get('title', None)
        image= kwargs.get('image', True)
        fields = kwargs.get('add_fields', False)
        footer = kwargs.get("add_footer", False)
        set_image = kwargs.get("set_image", False)
        set_url = kwargs.get("set_url", False)
        em=embedmanager(self, args[0], image, title, fields, footer, set_image, set_url)
        # print("processing:", time.time()-self.timer)

        try:
            return await super().send(em[0], embed=em[1])
        except Exception as e:
            print(e)
            string = "```PY\n" + args[0] + "```"
            return await super().send(string)

    async def get_cluster(self):
        cluster = await self.db.fetchrow("SELECT cluster_id FROM cluster WHERE guild_id = $1", self.guild.id)
        if cluster:
            self.cluster_id = cluster["cluster_id"]

    
    async def _acquire(self, timeout):
        if self.db is None:
            self.db = await self.pool.acquire(timeout=timeout)

        # Do stuff here right when the context is aquired
        await self.get_cluster()

        return self.db

    def acquire(self, *, timeout=None):
        """Acquires a database connection from the pool. e.g. ::
            async with ctx.acquire():
                await ctx.db.execute(...)
        or: ::
            await ctx.acquire()
            try:
                await ctx.db.execute(...)
            finally:
                await ctx.release()
        """
        return _ContextDBAcquire(self, timeout)
    async def release(self):
        """Releases the database connection from the pool.
        Useful if needed for "long" interactive commands where
        we want to release the connection and re-acquire later.
        Otherwise, this is called automatically by the bot.
        """
        # from source digging asyncpg source, releasing an already
        # released connection does nothing

        if self.db is not None:
            await self.bot.pool.release(self.db)
            self.db = None