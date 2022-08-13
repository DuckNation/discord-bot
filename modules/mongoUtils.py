import io
import json
import typing

import discord

from main import Duck

uuid_skin_mapping: typing.Dict[str, str] = {}
embed_color_mapping: typing.Final[typing.Dict[str, int]] = {
    "chat": discord.Colour.green(),
    "quit": discord.Colour.red(),
    "join": discord.Colour.blue(),
    "death": discord.Colour.dark_red(),
    "advancement": discord.Colour.yellow(),
}


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


async def handle_player_stuff(_type: str, doc: dict, bot: Duck, webhook: discord.Webhook):
    await bot.db.duckMinecraft.messages.update_one(doc, {"$set": {'ack': 1}})  # documents must be the same size.
    if _type == 'player_count':
        channel: discord.TextChannel = bot.get_channel(927300714508730418)
        await channel.edit(topic=str(doc['message']))
        await bot.db.duckMinecraft.messages.update_one(doc, {"$set": {'ack': 1}})  # documents must be the same size.
        # todo edit an embed that contains all online players.
        return
    if doc['playerUUID'] not in uuid_skin_mapping:
        uuid_skin_mapping[doc['playerUUID']] = f"https://api.tydiumcraft.net/v1/players/skin?uuid={doc['playerUUID']}&type=avatar"

    if _type == 'chat':
        await webhook.send(username=doc['playerName'], content=doc['message'], avatar_url=uuid_skin_mapping[doc['playerUUID']], allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=False))
        return

    # everything else
    embed = discord.Embed(description=doc['message'], colour=embed_color_mapping[_type], timestamp=discord.utils.utcnow())
    await webhook.send(username=doc['playerName'], embed=embed, avatar_url=uuid_skin_mapping[doc['playerUUID']], allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=False))

