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
        self.channel: discord.TextChannel

    @tasks.loop(seconds=1, count=1)
    async def setup_task(self):
        if not self.ready:
            self.ready = True
            await self.bot.wait_until_ready()
            self.channel: discord.TextChannel = self.bot.get_channel(927300714508730418)
            chat_channels = await self.session.get(f"{self.bot.api_url}/chats/get?key={self.bot.api_key}&uuid_or_id=False")
            chat_channels = await chat_channels.json()
            chat_channels.append({"global": 927300714508730418})

            for entry in chat_channels:
                path = next(iter(entry))
                path = entry[path]
                channel_id = entry['discordId'] if 'discordId' in entry else None

                if not channel_id:
                    await self.create_channel(path, entry['name'])
                else:
                    asyncio.ensure_future(self.connect(path, channel_id))

    async def cog_load(self):
        self.setup_task.start()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.ready:
            self.ready = True
            self.channel = self.bot.get_channel(927300714508730418)
            self.mapping["global"] = self.channel.id

    async def connect(self, path, channel_id):
        print(f"{self.bot.wss_url}/{path}?key={self.bot.api_key}")
        async with websockets.connect(f"{self.bot.wss_url}/{path}?key={self.bot.api_key}") as ws:
            self.ws_mapping[channel_id] = ws
            self.mapping[path] = channel_id
            while True:
                msg = await ws.recv()
                split = msg.split(";")
                if split[0] == "create_discord_channel":
                    await self.create_channel(split[1], split[2])
                if split[0] == "remove_player":
                    await self.remove_player(split[1], split[2])
                if split[0] == "update":
                    await self.channel.edit(topic=split[1])
                if split[0] == "chat":
                    await self.chat(self.mapping[path], msg.split(";", maxsplit=1)[1])
                if split[0] == "join":
                    await self.channel.send(embed=discord.Embed(description=split[1], colour=discord.Colour.green()))
                if split[0] == "leave":
                    await self.channel.send(embed=discord.Embed(description=split[1], colour=discord.Colour.red()))

    async def create_channel(self, internal_id: str, name: str):
        if internal_id in self.mapping:
            return
        async with self.session.get(
                f"{self.bot.api_url}/chats/get?key={self.bot.api_key}&chat_uuid={internal_id}") as resp:
            data = await resp.json()
        _id = data['discordId'] if 'discordId' in data else None
        if 'discordId' not in data:
            thread = await self.channel.create_thread(type=None, invitable=True, auto_archive_duration=10080, name=name)
            _id = thread.id
            await self.session.put(
                f"{self.bot.api_url}/chats/set-discord?key={self.bot.api_key}&chat_uuid={internal_id}&channel_id={_id}")

        self.mapping[internal_id] = _id
        asyncio.create_task(self.connect(internal_id, _id))

    async def chat(self, channel_id: int, message: str):
        await self.bot.get_channel(channel_id).send(message, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id in self.ws_mapping:
            hex_color = self.get_hex(message.author.top_role.color.to_rgb())
            await self.ws_mapping[message.channel.id].send(f"chat;<blue>[Discord]</blue> <color:{hex_color}>{message.author.name}</color:{hex_color}><gray>:</gray> <reset>{message.content}")

    # @commands.Cog.listener()
    async def on_thread_member_join(self, thread_member: discord.ThreadMember):
        guild = thread_member.thread.guild
        if guild.get_member(thread_member.id).bot:
            return
        if guild.get_member(thread_member.id).guild_permissions.manage_messages:
            return
        await thread_member.thread.last_message.add_reaction("🔃")
        data = await self.session.get(f"{self.bot.api_url}/info/stats?key={self.bot.api_key}&uid={thread_member.id}")
        if data.status != 200:
            await thread_member.thread.remove_user(discord.Object(thread_member.id))
            await thread_member.thread.send(embed=discord.Embed(description="That member has not connected to the server!", colour=discord.Colour.red()))
            return
        data = await data.json()
        if not data['uid']:
            await thread_member.thread.remove_user(discord.Object(thread_member.id))
            await thread_member.thread.send(embed=discord.Embed(description="That member has not verified their discord!", colour=discord.Colour.red()))
            return
        await thread_member.thread.send(embed=discord.Embed(description=f"Welcome <@{thread_member.id}>! ({data['username']})", colour=discord.Colour.green()))

    def get_hex(self, rgb: tuple):
        return '#%02x%02x%02x' % rgb

    async def remove_player(self, channel_id, player_id):
        request = await self.session.get(f"{self.bot.api_url}/info/stats?key={self.bot.api_key}&uid={player_id}")
        pass


async def setup(bot):
    await bot.add_cog(SMP(bot))
