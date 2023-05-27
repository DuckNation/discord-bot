import asyncio

import aioredis
import async_timeout
import discord
from discord.ext import commands, tasks


class SMP(commands.Cog):
    def __init__(self, bot):
        self.ready = False
        self.bot = bot

    @tasks.loop(seconds=1, count=1)
    async def setup_task(self):
        self.channel: discord.TextChannel = self.bot.get_channel(927300714508730418)
        pubsub = self.bot.redis.pubsub()
        await pubsub.subscribe("toDiscord")
        future = asyncio.create_task(self.reader(pubsub))
        await future

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.ready:
            self.ready = True
            self.channel = self.bot.get_channel(927300714508730418)
            pubsub = self.bot.redis.pubsub()
            await pubsub.subscribe("toDiscord")
            future = asyncio.create_task(self.reader(pubsub))
            await future

    # async def cog_load(self) -> None:
    #     self.setup_task.start()

    async def reader(self, channel: aioredis.client.PubSub):
        while True:
            try:
                async with async_timeout.timeout(1):
                    message = await channel.get_message(ignore_subscribe_messages=True)
                    if message:
                        data = bytes(message["data"]).decode("utf-8")
                        print(data)
                        await self.handle_type(data.split(';')[0], ';'.join(data.split(';')[1:]))
                    await asyncio.sleep(0.01)
            except asyncio.TimeoutError:
                pass

    async def handle_type(self, _type, msg):
        # enum_type = ChatEnums(_type)

        if _type == 'join':
            await self.channel.send(embed=discord.Embed(description=msg, color=discord.Color.green()))
        elif _type == 'leave':
            await self.channel.send(embed=discord.Embed(description=msg, color=discord.Color.red()))
        elif _type == 'chat':
            await self.channel.send(msg, allowed_mentions=discord.AllowedMentions.none())
        elif _type == 'update':
            await self.channel.edit(topic=msg)
        elif _type == 'death':
            await self.channel.send(embed=discord.Embed(description=msg, color=discord.Color.red()))
        else:
            await self.channel.send("<@578006934507094016>",
                                    embed=discord.Embed(description=msg, color=discord.Color.red()))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel == self.channel:
            await self.bot.redis.publish("toMinecraft",
                                         f"chat;<blue>[Discord]</blue> <dark_green>{message.author.name}</dark_green><gray>:</gray> <reset>{message.content}")


async def setup(bot):
    await bot.add_cog(SMP(bot))
