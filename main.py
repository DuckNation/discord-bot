import asyncio
import json
import traceback

import aiohttp
import aioredis
import discord
import discord.ext
from discord.ext import commands

from modules.booster_redis import Boosters

config = json.load(open("config.json"))

_modules = (
    "jishaku",
    "modules.smp",
    "modules.booster"
)


class Duck(commands.Bot):
    def __init__(self, **kwargs):
        self.redis = None
        self.sqlite = None
        self.api_key: str = config["api-key"]
        self.api_url: str = config["api-url"]
        self.wss_url: str = config["wss-url"]
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
            f"redis://{config['redis-ip']}:{config['redis-port']}", username="default",
            password=config["redis-password"])
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
    asyncio.run(
        Duck().start(config["bot-token"], reconnect=True)
    )
