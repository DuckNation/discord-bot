import asyncio
import sqlite3
import time

import aiohttp
import aiosqlite
import discord
import pymongo
from discord.ext import commands, tasks


class ChatEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.failed_attempts = {}
        self.sqlite: aiosqlite.Connection = bot.sqlite

    @commands.Cog.listener()
    async def on_ready(self):
        a: aiosqlite.Cursor = await self.sqlite.cursor()
        await a.execute("CREATE TABLE IF NOT EXISTS removeok(victim TEXT, unix TEXT)")
        await self.sqlite.commit()
        await a.close()
        self.unokay.start()

    @tasks.loop(hours=1)
    async def unokay(self):
        self.failed_attempts = {}
        a: aiosqlite.Cursor = await self.sqlite.cursor()
        this = await a.execute(
            "SELECT victim FROM removeok WHERE unix <= ?", (str(int(time.time())),)
        )
        rr = await this.fetchall()
        guild: discord.Guild = self.bot.get_guild(790774812690743306)
        for thing in rr:
            user = guild.get_member(int(thing[0]))
            if user:
                await user.remove_roles(
                    guild.get_role(896521055873667074), reason="okayed"
                )
                await a.execute("DELETE FROM removeok WHERE victim = ?", (thing[0],))
                await self.sqlite.commit()
        await a.close()
    @commands.Cog.listener(name="on_message")
    async def shoe_is_gay(self, message: discord.Message):
        if message.channel.id == 834581735642628147: return
        if message.author.id not in (713865980526329887, 821647232801570866): return
        if message.content == "ok": await message.delete()
    @commands.Cog.listener(name="on_message")
    async def on_okay(self, message: discord.Message):
        if message.channel.id != 834581735642628147:
            return
        if message.content == "ok":
            return
        await message.delete()
        try:
            if not self.failed_attempts[message.author.id]:
                self.failed_attempts[message.author.id] = 0
        except KeyError:
            self.failed_attempts[message.author.id] = 0

        self.failed_attempts[message.author.id] = (
            self.failed_attempts[message.author.id] + 1
        )

        if self.failed_attempts[message.author.id] > 2:
            await message.author.add_roles(
                message.guild.get_role(896521055873667074), reason="not okay >:("
            )
            a: aiosqlite.Cursor = await self.sqlite.cursor()
            await a.execute(
                "INSERT INTO removeok(victim, unix) VALUES (?, ?)",
                (str(message.author.id), str(int(time.time()) + 86400)),
            )  # 1 day
            await self.sqlite.commit()
            await a.close()

    @unokay.before_loop
    async def before_ok(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ChatEvents(bot))
