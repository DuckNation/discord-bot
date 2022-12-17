import asyncio

import aioredis
import async_timeout
from discord.ext import commands, tasks
import discord


class SMPListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel: discord.TextChannel = None
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
            self.channel = self.bot.get_channel(927300714508730418)
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
                        await self.handle_type(bytes(message["data"]).decode("utf-8"))
                    await asyncio.sleep(0.01)
            except asyncio.TimeoutError:
                pass


    async def handle_type(self, message: str):
        _type = message.split(";")[0]
        message = message.split(";")[1]
        match _type:
            case "online":
                await self.channel.edit(topic=f"""Join at **smp.quack.tk**! **{message}/25** Players Online.
                        19132 - Bedrock (Default)
                        25565 - Java (Default)""")
            case "chat":
                await self.channel.send(message, allowed_mentions=discord.AllowedMentions.none())
            case "join":
                await self.channel.send(embed=discord.Embed(description=f"{message} joined the game.", colour=discord.Colour.green()), allowed_mentions=discord.AllowedMentions.none())
            case "leave":
                await self.channel.send(embed=discord.Embed(description=f"{message} left the game.", colour=discord.Colour.orange()), allowed_mentions=discord.AllowedMentions.none())
            case "death":
                await self.channel.send(embed=discord.Embed(description=f"{message}", colour=discord.Colour.red()), allowed_mentions=discord.AllowedMentions.none())
            case "advancement":
                await self.channel.send(embed=discord.Embed(description=f"{message}", colour=discord.Colour.blue()), allowed_mentions=discord.AllowedMentions.none())







async def setup(bot):
    await bot.add_cog(SMPListener(bot))