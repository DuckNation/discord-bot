import asyncio
import os
import traceback

import aiohttp
import discord
import discord.ext
from discord.ext import commands
from redis import asyncio as aioredis

from modules.booster_redis import Boosters

_modules = ("jishaku", "modules.smp", "modules.booster")


class Duck(commands.Bot):
    def __init__(self, **kwargs):
        self.redis = None
        self.sqlite = None
        self.api_key: str = os.getenv("API_KEY")
        self.api_url: str = os.getenv("API_URL")
        self.wss_url: str = os.getenv("WSS_URL")
        allowed_mentions = discord.AllowedMentions(
            roles=False, everyone=False, users=True
        )
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            voice_states=True,
            messages=True,
            message_content=True,
        )
        super().__init__(
            command_prefix=["."],
            allowed_mentions=allowed_mentions,
            case_insensitive=True,
            strip_after_prefix=True,
            intents=intents,
        )

    async def setup_hook(self) -> None:
        self.redis: aioredis.ConnectionPool = await aioredis.from_url(
            f"redis://{os.getenv('REDIS_IP')}:{os.getenv('redis-port')}",
            username="default",
            password=os.getenv("redis-password"),
        )
        self.session = aiohttp.ClientSession()
        await Boosters(self.redis).load_cache()
        for ext in _modules:
            try:
                await self.load_extension(ext)
                print(f"Loaded {ext}")
            except Exception as e:
                print(e)
                print(f"Failed to load {ext}")
                traceback.print_tb(e.__traceback__)

    async def close(self) -> None:
        await self.session.close()
        await self.sqlite.close()
        await self.close()

    async def on_ready(self):
        print("Bot is ready.")


# async def main():
#     duck = Duck()
#     async with duck:
#         # client.loop.create_task(background_task())
#         await duck.start(config["bot-token"])
#         # await Duck().sync()

if __name__ == "__main__":
    asyncio.run(Duck().start(os.getenv("bot-token"), reconnect=True))
