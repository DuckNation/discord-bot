import asyncio
import pprint
import traceback

import aiohttp
import discord
import websockets
from discord.ext import commands, tasks

from modules.smp.role_listener import get_highest_level_role, SMPListener


def get_hex(rgb: tuple):
    return "#%02x%02x%02x" % rgb


class SMP(commands.Cog):
    def __init__(self, bot):
        self.ready = False
        self.bot: commands.Bot = bot
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
            chat_channels = await self.session.get(
                f"{self.bot.api_url}/chats/better-get?key={self.bot.api_key}"
            )
            chat_channels = await chat_channels.json()
            chat_channels.append(
                {"name": "global", "uuid": "global", "discordId": self.channel.id}
            )

            for entry in chat_channels:
                path = entry["uuid"]
                channel_id = entry["discordId"] if "discordId" in entry else None
                channel_id = None if channel_id == -1 else channel_id
                name = entry["name"]

                if not channel_id:
                    await self.create_channel(path, name)
                else:
                    asyncio.ensure_future(self.connect(path, channel_id))

    async def cog_load(self):
        self.setup_task.start()

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel = self.bot.get_channel(927300714508730418)
        self.mapping["global"] = self.channel.id

        # await asyncio.sleep(2)

        await self.add_users()

    async def add_users(self):
        guild = self.bot.get_guild(790774812690743306)
        for member in guild.members:
            if member.bot:
                continue

            data = await self.session.get(
                f"{self.bot.api_url}/info/stats?key={self.bot.api_key}&uid={member.id}"
            )
            data = await data.json()
            if "detail" in data:
                continue

            channels = await self.session.get(
                f"{self.bot.api_url}/chats/better-get?key={self.bot.api_key}&player_uuid={data['uuid']}"
            )

            channels = await channels.json()
            print(channels)

            for channel in channels:
                if "discordId" not in channel:
                    continue
                if channel["discordId"] == self.channel.id:
                    continue

                thread: discord.Thread = self.bot.get_channel(channel["discordId"])

                if not thread:
                    continue

                try:
                    await thread.add_user(discord.Object(id=member.id))
                except discord.Forbidden:
                    pass
                await asyncio.sleep(0.5)

    async def connect(self, path, channel_id):
        should_connect = True
        while should_connect:
            try:
                print(f"Connecting to {path}")
                async with websockets.connect(
                    f"{self.bot.wss_url}/{path}?key={self.bot.api_key}"
                ) as ws:
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
                            await self.chat(
                                self.mapping[path], msg.split(";", maxsplit=1)[1]
                            )
                        if split[0] == "join":
                            await self.channel.send(
                                embed=discord.Embed(
                                    description=split[1], colour=discord.Colour.green()
                                )
                            )
                        if split[0] == "leave":
                            await self.channel.send(
                                embed=discord.Embed(
                                    description=split[1], colour=discord.Colour.red()
                                )
                            )
                        if split[0] == "delete_discord_channel":
                            await self.bot.get_channel(int(split[1])).delete()
                            if not path == "global":
                                should_connect = False
                                break
            except websockets.ConnectionClosedError | websockets.ConnectionClosedError:
                await self.chat(
                    self.mapping[path], "Connection closed to chat, reconnecting..."
                )
                await asyncio.sleep(10)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                await self.chat(
                    self.mapping[path],
                    "I was unable to reconnect to the chat, spam haappi.",
                )
                return

    async def create_channel(self, internal_id: str, name: str):
        if internal_id in self.mapping:
            return
        async with self.session.get(
            f"{self.bot.api_url}/chats/get?key={self.bot.api_key}&chat_uuid={internal_id}&uuid_or_id=False"
        ) as resp:
            data = await resp.json()
        _id = data["discordId"] if "discordId" in data else None
        if "discordId" not in data or data['discordId'] is None or data['discordId'] == -1:
            thread = await self.channel.create_thread(
                type=None, invitable=True, auto_archive_duration=10080, name=name
            )
            _id = thread.id
            await self.session.put(
                f"{self.bot.api_url}/chats/set-discord?key={self.bot.api_key}&chat_uuid={internal_id}&channel_id={_id}"
            )

        self.mapping[internal_id] = _id
        asyncio.create_task(self.connect(internal_id, _id))

    async def chat(self, channel_id: int, message: str):
        await self.bot.get_channel(channel_id).send(
            message, allowed_mentions=discord.AllowedMentions.none()
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id in self.ws_mapping:
            hex_color = get_hex(message.author.top_role.color.to_rgb())
            await self.ws_mapping[message.channel.id].send(
                f"chat;<blue>[Discord]</blue> <color:{hex_color}>{message.author.name}</color:{hex_color}><gray>:</gray> <reset>{message.clean_content}"
            )

    @commands.command()
    async def unverify(self, ctx: commands.Context):
        to_remove = await self.session.delete(
            f"{self.bot.api_url}/verification/unverify?key={self.bot.api_key}&uid={ctx.author.id}"
        )
        if not to_remove.status == 200:
            return await ctx.send("You are not verified.")
        await ctx.send("Successfully unverified.")
        for thread in self.channel.threads:
            for mem in thread.members:
                if mem.id == ctx.author.id:
                    try:
                        await thread.remove_user(discord.Object(id=ctx.author.id))
                    except discord.HTTPException:
                        pass

    @commands.command()
    async def verify(self, ctx: commands.Context, pin: str):
        data = await self.session.post(
            f"{self.bot.api_url}/verification/verify?key={self.bot.api_key}&uid={ctx.author.id}&pin={pin}"
        )
        _json = await data.json()
        if data.status != 200:
            return await ctx.send(_json["detail"])
        await ctx.send(_json["message"])

        role = get_highest_level_role(ctx.author.roles)

        command = (
            "lpv user {username} parent add group.%s"
            % SMPListener.role_mapping[role.id]
        )

        await self.bot.session.patch(
            f"{self.bot.api_url}/info/permissions?uid={ctx.author.id}&permission={command}&key={self.bot.api_key}"
        )

    @commands.command()
    async def who(self, ctx: commands.Context, user: discord.Member | int | None):
        if not user:
            return await ctx.send("Please specify a user.")

        data = await self.session.get(
            f"{self.bot.api_url}/info/stats?key={self.bot.api_key}&uid={user.id if isinstance(user, discord.Member) else user}"
        )
        data = await data.json()
        if not data:
            return await ctx.send("User not found.")
        if "detail" in data:
            return await ctx.send(data["detail"])

        return await ctx.send(
            embed=discord.Embed(
                description=f"Username: {data['username']}\n"
                f"UUID: {data['uuid']}\n"
                f"Discord: <@{data['uid'] if 'uid' in data else 'NA'}>\n"
            )
        )

    async def remove_player(self, channel_id, player_id):
        request = await self.session.get(
            f"{self.bot.api_url}/info/stats?key={self.bot.api_key}&uid={player_id}"
        )
        pass


async def setup(bot):
    await bot.add_cog(SMP(bot))
