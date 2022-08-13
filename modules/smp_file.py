import asyncio
import json

import discord
import pymongo
from discord.ext import commands
from pymongo.collection import Collection

from main import Duck
from modules.mongoUtils import handle_change_mob, handle_config_upload


async def pain(collection: Collection, bot: Duck) -> None:
    await bot.wait_until_ready()
    cursor = collection.find(
        (), cursor_type=pymongo.CursorType.TAILABLE_AWAIT, oplog_replay=True
    )
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
                await handle_config_upload(doc, webhook)
            elif doc["type"] == "chat":
                pass
            elif doc["type"] == "change_mob":
                await handle_change_mob(doc, bot)
            else:
                await webhook.send(doc)
        await asyncio.sleep(1)

    await asyncio.sleep(5)
    await pain(
        collection,
        bot,
    )


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
                self.collection,
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
