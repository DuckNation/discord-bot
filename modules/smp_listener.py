import asyncio

import aioredis
import async_timeout
from discord.ext import commands, tasks
import discord


class SMPListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis: aioredis.ConnectionPool = bot.redis
        self.ready = False

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
        try:
            await self.redis.publish("minecraft", f"<blue>[Discord]</blue> <dark_green>{message.author.display_name}</dark_green><gray>:</gray> <reset>{message.content}")
        except Exception as e:
            print(e)
        print("a")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.ready:
            self.ready = True
            pubsub = self.redis.pubsub()
            await pubsub.subscribe("discord")
            future = asyncio.create_task(self.reader(pubsub))
            await future

    async def reader(self, channel: aioredis.client.PubSub):
        while True:
            try:
                async with async_timeout.timeout(1):
                    message = await channel.get_message(ignore_subscribe_messages=True)
                    if message is not None:
                        await self.bot.get_channel(927300714508730418).send(str(message["data"]), allowed_mentions=discord.AllowedMentions.none())
                    await asyncio.sleep(0.01)
            except asyncio.TimeoutError:
                pass




async def setup(bot):
    await bot.add_cog(SMPListener(bot))