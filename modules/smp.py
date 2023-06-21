import asyncio

import aiohttp
import discord
import websockets
from discord.ext import commands, tasks


class SMP(commands.Cog):
    def __init__(self, bot):
        self.ready = False
        self.bot = bot
        self.session: aiohttp.ClientSession = bot.session
        self.mapping = {}
        self.ws_mapping = {}

    @tasks.loop(seconds=1, count=1)
    async def setup_task(self):
        self.channel: discord.TextChannel = self.bot.get_channel(927300714508730418)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.ready:
            self.ready = True
            self.channel = self.bot.get_channel(927300714508730418)
            self.mapping["global"] = self.channel.id
            task = asyncio.ensure_future(self.connect("global", 927300714508730418))
            await task

    async def connect(self, path, channel_id):
        async with websockets.connect(f"wss://quack.boo/internal/api/wss/{path}?key={self.bot.api_key}") as ws:
            self.ws_mapping[channel_id] = ws
            while True:
                msg = await ws.recv()
                split = msg.split(";")
                print(split)
                if split[0] == "create_discord_channel":
                    await self.create_channel(split[1], split[2])
                if split[0] == "update":
                    await self.channel.edit(topic=split[1])
                if split[0] == "chat":
                    await self.chat(self.mapping[path], split[1])
                if split[0] == "join":
                    await self.channel.send(embed=discord.Embed(description=split[1], colour=discord.Colour.green()))
                if split[0] == "leave":
                    await self.channel.send(embed=discord.Embed(description=split[1], colour=discord.Colour.red()))

    async def create_channel(self, internal_id: str, name: str):
        if internal_id in self.mapping:
            return
        async with self.session.get(
                f"http://127.0.0.1:6420/api/chats/get?key={self.bot.api_key}&chat_uuid={internal_id}") as resp:
            data = await resp.json()
            if len(data) != 1:
                return
            data = data[0]
        _id = data['discord_id'] if 'discord_id' in data else None
        if 'discord_id' not in data:
            thread = await self.channel.create_thread(type=None, invitable=True, auto_archive_duration=10080, name=name)
            _id = thread.id
            await self.session.put(
                f"http://127.0.0.1:6420/api/chats/set-discord?key={self.bot.api_key}&chat_uuid={internal_id}&channel_id={_id}")

        self.mapping[internal_id] = _id
        asyncio.create_task(self.connect(internal_id, _id))

    async def chat(self, channel_id: int, message: str):
        await self.bot.get_channel(channel_id).send(message, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id in self.ws_mapping:
            await self.ws_mapping[message.channel.id].send(f"chat;<blue>[Discord]</blue> <dark_green>{message.author.name}</dark_green><gray>:</gray> <reset>{message.content}")


async def setup(bot):
    await bot.add_cog(SMP(bot))
