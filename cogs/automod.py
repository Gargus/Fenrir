from discord.ext import commands

class AutomodCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def message_check(self, message, feature, channels):
        try:
            func = getattr(self, feature)
        except AttributeError:
            pass
        check = await func(message, channels)
        if check:
            try:
                await message.delete()
            except Exception:
                pass

    async def image_check(self, message, channels):
        if str(message.channel.id) in channels:
            if not message.attachments and not message.embeds:
                return True


def setup(bot):
    bot.add_cog(AutomodCog(bot))
