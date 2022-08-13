import json

import discord

from main import Duck


async def handle_change_mob(doc: dict, bot: Duck):
    channel: discord.TextChannel = bot.get_channel(927300714508730418)
    embed: discord.Embed = discord.Embed(
        description=f"Current Totem Mob: **{doc['mobName']}**", colour=discord.Colour.random(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text="Last Updated at: ")
    await bot.get_channel(927300714508730418).get_partial_message(1006353427862917222).edit(
        embed=embed,
        content=None,
    )
    await channel.send(doc['message'])

    await bot.db.duckMinecraft.messages.update_one(doc, {"$set": {'ack': 1}})  # documents must be the same size.


async def handle_config_upload(doc: dict, webhook: discord.Webhook):
    del doc["file"]
    await webhook.send(
        doc["message"],
        embed=discord.Embed(
            description=json.dumps(doc["returned"], indent=4)
        ),
        allowed_mentions=discord.AllowedMentions(
            everyone=False, users=True, roles=False
        ),
    )
