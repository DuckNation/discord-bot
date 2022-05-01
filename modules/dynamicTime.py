import asyncio
from datetime import datetime

import aiosqlite
import pytz
from discord.ext import commands
import discord

from modules.utils import time


class DynamicTime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sqlite: aiosqlite.Connection = bot.sqlite

    async def cog_load(self) -> None:
        await self.sqlite.execute("CREATE TABLE IF NOT EXISTS timezones (user_id INTEGER, timezone TEXT)")
        await self.sqlite.commit()

    @commands.group(invoke_without_command=True, name="time")
    async def _time(self, ctx):
        pass

    @_time.command()
    async def setup(self, ctx: commands.Context):
        def is_correct(m):
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.reply("What's the current time for you?\nInput your time as 24 hour standard (14:54)",
                        delete_after=21)
        try:
            _time = await self.bot.wait_for('message', check=is_correct, timeout=20.0)
        except asyncio.TimeoutError:
            return await ctx.send("Timed out.")
        hour = _time.content.split(':')[0]
        minute = _time.content.split(':')[1]
        now = datetime.now(pytz.utc)
        possible_vals = \
            [tz for tz in pytz.common_timezones_set if now.astimezone(pytz.timezone(tz)).hour == int(hour) and
             now.astimezone(pytz.timezone(tz)).minute == int(minute)]
        if len(possible_vals) == 0:
            return await ctx.send("Invalid time. Please try again.")
        embed = discord.Embed(title="Timezones", description="\n".join(possible_vals))
        await ctx.send(embed=embed, content="Pick the timezone you're in")

        try:
            _time = await self.bot.wait_for('message', check=is_correct, timeout=20.0)
        except asyncio.TimeoutError:
            return await ctx.send("Timed out.")
        if _time.content not in possible_vals:
            return await ctx.send("That's not a valid timezone.")
        await ctx.send("Setting timezone to {}".format(_time.content))
        await self.sqlite.execute("DELETE FROM timezones WHERE user_id = ?", (ctx.author.id,))
        await self.sqlite.commit()
        await self.sqlite.execute("INSERT INTO timezones (user_id, timezone) VALUES (?, ?)",
                                  (ctx.author.id, _time.content,))
        await self.sqlite.commit()

    @_time.command()
    async def get(self, ctx: commands.Context, *,
                  when: time.UserFriendlyTime(commands.clean_content, default='\u2026')):
        tz = await self.get_timezone(ctx.author.id)
        dt_now = datetime.now(pytz.timezone(tz))
        print(int(when.dt.timestamp()) - int(dt_now.timestamp()))
        # yes = now.astimezone(when.dt.tzinfo)
        # print(yes.timestamp())
        # b = (int(when.dt.timestamp()) - now.timestamp())
        # a = int(now.timestamp()) + (int(datetime.now(when.dt.tzinfo).timestamp()) - int(now.timestamp()))
        # a = int(datetime.now(when.dt.tzinfo).timestamp()) + (int(when.dt.timestamp()) - int(now.timestamp()))
        # print((int(when.dt.timestamp()) - int(now.timestamp())))
        # await ctx.send(f"\<t:{int(int(now.timestamp()) + b)}>. Which is \<t:{int(int(now.timestamp()) + b)}:R>")

    # @_time.command()
    # async def get(self, ctx: commands.Context):
    #
    #     tz = await self.get_timezone(ctx.author.id)
    #     now = datetime.now(pytz.timezone(tz))
    #     await ctx.send(f"It's currently {now.strftime('%H:%M')} in {tz}")

    async def get_timezone(self, user_id):
        async with self.sqlite.execute("SELECT timezone FROM timezones WHERE user_id = ?", (user_id,)) as cursor:
            a = await cursor.fetchone()
            if not a:
                return "Etc/GMT"
            return a[0]


async def setup(bot):
    await bot.add_cog(DynamicTime(bot))
