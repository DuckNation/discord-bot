import asyncio
import json

import discord
import pymongo
from discord.ext import commands
from pymongo.collection import Collection
from pymongo.cursor import Cursor


async def pain(cursor: Cursor, bot: commands.Bot) -> None:
    await bot.wait_until_ready()
    webhook: discord.Webhook = discord.Webhook.from_url(
        "https://discord.com/api/webhooks/1006624911990718464/PT8h7zGxQcd5HDz2CN6LX6ZmJn69aO9W8ci0UgaYdvgW6XeLWbXxoWPMmzM7h5lwuTpB",
        session=bot.session,
    )

    while cursor.alive:
        async for doc in cursor:  # noqa
            if doc["bound"] != "clientbound":
                continue
            if 'ack' in doc and doc['ack'] == 1:
                continue
            if doc["type"] == "config":
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
            elif doc["type"] == "chat":
                pass
            elif doc["type"] == "change_mob":
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

                await bot.db.duckMinecraft.messages.update_one(doc, {"$set": {'ack': 1}}) # documents must be the same size.
            else:
                await webhook.send(doc)
        await asyncio.sleep(1)


def use_files():
    def predicate(ctx: commands.Context):
        return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == 851127222629957672  # Juno
        )

    return commands.check(predicate)


class SMPFile(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.db: pymongo.MongoClient = bot.db
        self.collection: Collection = self.bot.db.get_database(
            "duckMinecraft"
        ).get_collection("messages")

    async def cog_load(self) -> None:
        asyncio.create_task(
            pain(
                self.collection.find(
                    (), cursor_type=pymongo.CursorType.TAILABLE_AWAIT, oplog_replay=True
                ),
                self.bot,
            )
        )

    @commands.command()
    @use_files()
    async def upload(self, ctx: commands.Context, index: int = 0):
        if not ctx.message.attachments:
            return await ctx.send("No attachments found!")

        if (
                not ctx.message.attachments[0].filename.endswith(".yml")
                # or not ctx.message.attachments[0].filename.endswith(".yaml")
                # or not ctx.message.attachments[0].filename.endswith(".properties")
                # or not ctx.message.attachments[0].filename.endswith(".json")
        ):
            return await ctx.send(
                "Invalid file type! Must be either a `.yml`, `.properties` or `.json` file."
            )

        attach = await ctx.message.attachments[0].read()
        await self.collection.insert_one(
            {
                "type": "config",
                "bound": "serverbound",
                "file": attach,
                "fileName": ctx.message.attachments[0].filename,
                "index": index,
            }
        )
        await ctx.send("Uploaded!")


async def setup(bot):
    await bot.add_cog(SMPFile(bot))
