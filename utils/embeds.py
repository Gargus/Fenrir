import discord
import json
import re



def embedmanager(ctx, desc, image, title, fields, footer, set_image, set_url):

    hex = 0x222020
    url = "https://cdn.discordapp.com/attachments/366306537725100033/466400320344424449/fenrir2.png"

    # if donor
    try:
        if ctx.donor:
            url = ctx.donor["theme"]["url"]
            hex = int(ctx.donor["theme"]["hex"], 16)
    except Exception:
        pass

    em=discord.Embed(title=title, description=desc, colour=hex)
    string=f"{ctx.message.author.name} | {ctx.invoked_with}"
    em.set_author(name=string, icon_url=ctx.message.author.avatar_url)
    if image:
        em.set_thumbnail(url=url)
    elif set_url:
        em.set_thumbnail(url=set_url)
    if footer:
        em.set_footer(text=footer)
    if fields:
        for field in fields:
            try:
                data = field[2]
            except (ValueError, IndexError):
                em.add_field(name=field[0], value=field[1])
            else:
                em.add_field(name=field[0], value=field[1], inline=field[2])
    if set_image:
        em.set_image(url=set_image)
    return None, em