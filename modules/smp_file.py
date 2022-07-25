import asyncio
import json

import discord
import pymongo
from discord import utils
from discord.ext import commands
from pymongo.collection import Collection
from pymongo.cursor import Cursor


async def pain(cursor: Cursor, bot: commands.Bot) -> None:
    await bot.wait_until_ready()
    while cursor.alive:
        async for doc in cursor:  # noqa
            if doc["bound"] != "clientbound":
                continue
            del doc["file"]
            if doc["type"] == "config":
                print(doc)
                await bot.get_channel(1001007612923490304).send(
                    doc["message"],
                    embed=discord.Embed(
                        description=json.dumps(doc["returned"], indent=4)
                    ),
                )
            elif doc["type"] == "chat":
                pass
            else:
                await bot.get_channel(1001007612923490304).send(doc)
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

        # if the filename doesn't end in .yml
        if not ctx.message.attachments[0].filename.endswith(".yml"):
            return await ctx.send("Invalid file type! Must be a .yml file.")

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
