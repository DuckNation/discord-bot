import asyncio
import json

import async_timeout
import discord
import pymongo
from aioredis import Redis
from discord.ext import commands
from pymongo.collection import Collection
import aioredis

from modules.mongoUtils import handle_change_mob, handle_config_upload, handle_player_stuff


async def pain(collection: Collection, bot: commands.Bot) -> None:
    await bot.wait_until_ready()
    cursor = collection.find(
        (), cursor_type=pymongo.CursorType.TAILABLE_AWAIT, oplog_replay=True
    )
    webhook: discord.Webhook = discord.Webhook.from_url(
        "https://discord.com/api/webhooks/1006624911990718464"
        "/PT8h7zGxQcd5HDz2CN6LX6ZmJn69aO9W8ci0UgaYdvgW6XeLWbXxoWPMmzM7h5lwuTpB",
        session=bot.session,
    )

    while cursor.alive:
        async for doc in cursor:  # noqa
            if doc["bound"] != "clientbound":
                continue
            if 'ack' in doc and doc['ack'] == 1:
                continue
            match doc['type']:
                case 'change_mob':
                    await handle_change_mob(doc, bot)
                case 'config':
                    await handle_config_upload(doc, webhook)
                case 'chat' | 'quit' | 'join' | 'death' | 'advancement' | 'player_count':
                    await handle_player_stuff(doc['type'], doc, bot, webhook)
                case _:
                    print(f"Unknown type: {doc['type']}")
                    print(doc)
        await asyncio.sleep(1)

    await asyncio.sleep(5)
    await pain(
        collection,
        bot,
    )


async def reader(channel: aioredis.client.PubSub, bot: commands.Bot):
    webhook: discord.Webhook = discord.Webhook.from_url(
        "https://discord.com/api/webhooks/1006624911990718464"
        "/PT8h7zGxQcd5HDz2CN6LX6ZmJn69aO9W8ci0UgaYdvgW6XeLWbXxoWPMmzM7h5lwuTpB",
        session=bot.session,
    )
    while True:
        try:
            async with async_timeout.timeout(1):
                message = await channel.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    thing = json.loads(message['data'])
                    await handle_player_stuff(thing['type'], thing, bot, webhook)
                await asyncio.sleep(0.01)
        except asyncio.TimeoutError:
            pass


def use_files():
    def predicate(ctx: commands.Context):
        return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == 851127222629957672  # Juno
        )

    return commands.check(predicate)


async def redis_thing(bot) -> Redis:
    redis = aioredis.from_url("redis://smp.quack.tk")
    await redis.execute_command("AUTH",
                                "Vev9nBGCXbPVm6QGv+PPqqWd2ItmuASiJVXLweTVk2mJ1ZQeHA5nT9/+PW1nVgooANa0aVl6U0z285Va")
    pubsub = redis.pubsub()
    await pubsub.subscribe("discord")
    future = asyncio.create_task(reader(pubsub, bot))
    await future

    return redis


class SMPFile(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.db: pymongo.MongoClient = bot.db
        self.collection: Collection = self.bot.db.get_database(
            "duckMinecraft"
        ).get_collection("messages")
        self.task_redis = None

    async def cog_load(self) -> None:
        # asyncio.create_task(
        #     pain(
        #         self.collection,
        #         self.bot,
        #     )
        # )
        self.task_redis = asyncio.create_task(
            redis_thing(self.bot)
        )

    @commands.Cog.listener(name='on_message')
    async def on_discord_thing(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        if message.channel.id != 927300714508730418:
            return
        if not message.content:
            return
        if message.content == "":
            return

        role_color = message.author.top_role.color
        # await self.task_redis.publish("minecraft", "Hello")
        await self.collection.insert_one(
            {
                "type": "chat",
                "ack": 0,
                "bound": "serverbound",
                "message": f"<color:{role_color}>{message.author.display_name}</color>: {message.clean_content}",
            }
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
        await ctx.message.delete()
        await ctx.send("Uploaded!")


async def setup(bot):
    await bot.add_cog(SMPFile(bot))
