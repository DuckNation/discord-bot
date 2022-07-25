import asyncio
import json
import time
import typing

import discord
import pymongo
from bson import ObjectId
from discord.ext import commands
from discord.ext.commands import BucketType
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.results import InsertOneResult

from modules.utils import embeds


async def pain(cursor: Cursor) -> None:
    while cursor.alive:
        async for doc in cursor:
            print(doc)
        await asyncio.sleep(1)


class SMPFile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db: pymongo.MongoClient = bot.db
        self.collection: Collection = self.bot.db.get_database("duckMinecraft").get_collection("messages")

    async def cog_load(self) -> None:
        asyncio.create_task(pain(self.collection.find(({}), cursor_type=pymongo.CursorType.TAILABLE_AWAIT,
                                                      oplog_replay=True)))


async def setup(bot):
    await bot.add_cog(SMPFile(bot))
