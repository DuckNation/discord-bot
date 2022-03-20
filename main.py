import asyncio
import dis
import sys
import traceback
from typing import Literal

import aiohttp
import aiosqlite
import discord.ext
import discord

import logging
import os
import time
import json

from discord import app_commands
from discord.ext import commands
from discord.ext.commands import context
import motor.motor_asyncio
import pymongo

config = json.load(open("config.json"))

_modules = (
    "modules.utils.errorHandling",
    "modules.snipe",
    "modules.admin",
    "modules.antiOk",
    "modules.antiabuse",
)


class Duck(commands.Bot):
    def __init__(self, **kwargs):
        self.sqlite = None
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
            message_content=True,
        )
        super().__init__(
            command_prefix=["."],
            allowed_mentions=allowed_mentions,
            case_insensitive=True,
            strip_after_prefix=True,
            owner_ids=(
                578006934507094016,  # haappi
                255436078868070401,  # alys
                354297568165101569,  # scold
            ),
            intents=intents,
        )

    async def setup_hook(self) -> None:
        self.sqlite = await aiosqlite.connect("duck.db")
        self.session = aiohttp.ClientSession()
        for ext in _modules:
            try:
                await self.load_extension(ext)
                print(f"Loaded {ext}")
            except Exception as e:
                print(e)

    async def on_ready(self):
        print("Bot is ready.")
        # await self.load_extension('modules.slashPain')
        # self.tree.add_command(self.fruit, guild=discord.Object(id=790774812690743306))
        # self.loop.create_task(self.sync())


# async def main():
#     duck = Duck()
#     async with duck:
#         # client.loop.create_task(background_task())
#         await duck.start(config["bot-token"])
#         # await Duck().sync()


duck = Duck()
duck.run(config["bot-token"], reconnect=True)
