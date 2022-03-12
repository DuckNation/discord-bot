import asyncio
import sys
import traceback

import aiohttp
import discord.ext
import discord

import logging
import os
import time
import json
from discord.ext import commands
from discord.ext.commands import context
import motor.motor_asyncio
import pymongo

inital_cogs = (
    "jishaku",
    "modules.admin",
    "modules.community",
    "modules.chatEvents",
    "modules.snipe",
    "modules.events",
)

config = json.load(open("config.json"))


async def run():
    logger = logging.getLogger("discord")
    logger.setLevel(logging.WARNING)
    if not os.path.exists("logs"):
        os.makedirs("logs")
    handler = logging.FileHandler(
        filename=f"logs/discord-{int(time.time())}-.log",
        encoding="utf-8",
        mode="w",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
    )
    logger.addHandler(handler)
    session = aiohttp.ClientSession()
    client: pymongo.MongoClient = motor.motor_asyncio.AsyncIOMotorClient(
        config["database-uri"]
    )
    bot = Duck(db=client, session=session)

    try:
        # bpaT223O28SWA6MT
        await bot.start(
            config["bot-token"],  # main
            reconnect=True,
        )
    except KeyboardInterrupt:
        print("Bot is going byebye ;-;")
    finally:
        await bot.close()


class Duck(commands.Bot):
    def __init__(self, **kwargs):
        self.db: pymongo.MongoClient = kwargs.pop("db")
        self.session: aiohttp.ClientSession = kwargs.pop("session")
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
            reactions=True,
            presences=True,
        )
        super().__init__(
            command_prefix=["."],
            allowed_mentions=allowed_mentions,
            case_insensitive=True,
            strip_after_prefix=True,
            owner_ids=[
                578006934507094016,
            ],
            intents=intents,
        )
        self.remove_command("help")

        for extension in inital_cogs:
            try:
                self.load_extension(extension)
                print(f"Loaded {extension}")
            except discord.ext.commands.ExtensionNotFound:
                print(
                    f"-=-=-=-=-=-=-=-= Failed to load extension {extension}. Not found. -=-=-=-=-=-=-=-="
                )
                continue
            except Exception:
                print(f"Failed to load extension {extension}.", file=sys.stderr)
                traceback.print_exc()

    async def get_context(self, message, *, cls=context.Context):
        return await super().get_context(message, cls=cls)

    async def on_ready(self):
        print("Duck Bot has loaded!")

    async def close(self):
        await super().close()  # type: ignore
        await self.db.close()
        await self.session.close()

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def process_commands(self, message):
        if message.author.bot:
            return
        ctx = await self.get_context(message, cls=commands.Context)
        await self.invoke(ctx)


loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(run())
except KeyboardInterrupt:
    print("Bot is going offline... ByeBye")
