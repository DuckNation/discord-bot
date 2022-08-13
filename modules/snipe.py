import datetime
import time

import discord
from discord import utils
from discord.ext import commands, tasks

cant = ("ok", "nigg", "fag")


def cooldowns(message: discord.Message):
    if utils.get(message.author.roles, id=887547454885601350):
        return None
    elif utils.get(message.author.roles, id=888578948445900831):
        return commands.Cooldown(1, 5)
    elif utils.get(message.author.roles, id=888106876854763560):
        return commands.Cooldown(1, 15)
    #     elif message.author.id == 713865980526329887:  # no shoe just gucci
    #         return commands.Cooldown(1, 30)
    else:
        return commands.Cooldown(1, 60)


def use_snipe():
    def predicate(ctx: commands.Context):
        return (
            utils.get(ctx.author.roles, id=888578948445900831)
            or utils.get(ctx.author.roles, id=888106876854763560)
            or ctx.author.guild_permissions.administrator
            or ctx.author.id == 851127222629957672  # Juno
            or ctx.author.id == 903611946543251457  # Adj
        )

    return commands.check(predicate)


class Snipe(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.messages = {}
        self.edited = {}

    async def cog_load(self) -> None:
        self.clear_snipes.start()

    @tasks.loop(minutes=3)
    async def clear_snipes(self):
        self.messages = {}
        self.edited = {}

    @commands.command(aliases=["hiss"])
    @use_snipe()
    @commands.dynamic_cooldown(cooldowns, commands.BucketType.user)
    async def snipe(self, ctx: commands.Context, count: int = 1):
        if ctx.author.id == 434210851034103810:  # chosen
            await ctx.message.add_reaction("🥰")
        try:
            if not self.messages[ctx.channel.id]:
                self.messages[ctx.channel.id] = []
                return await ctx.send("No snipes were found!")
        except KeyError:
            self.messages[ctx.channel.id] = []
            return await ctx.send("No snipes were found!")
        messages: list = self.messages[ctx.channel.id]
        messages.reverse()
        if count > len(messages):
            # if ctx.author.id == 578006934507094016: return await ctx.send(len(messages)
            return await ctx.send("That snipe number is too high!", delete_after=5)
        message = self.messages[ctx.channel.id][count - 1].split("ß")
        embed = discord.Embed(
            description=message[2],
            colour=discord.Colour.random(),
            timestamp=datetime.datetime.fromtimestamp(int(message[1])),
        )
        sender: discord.User = await self.bot.fetch_user(int(message[0]))
        embed.set_author(name=str(sender), icon_url=sender.avatar.url)
        await ctx.send(embed=embed, delete_after=10)

    @commands.command(aliases=["es"])
    @use_snipe()
    @commands.dynamic_cooldown(cooldowns, commands.BucketType.user)
    async def editsnipe(self, ctx: commands.Context, count: int = 1):
        try:
            if not self.edited[ctx.channel.id]:
                self.edited[ctx.channel.id] = []
                return await ctx.send("No snipes were found!")
        except KeyError:
            self.edited[ctx.channel.id] = []
            return await ctx.send("No snipes were found!")
        messages: list = self.edited[ctx.channel.id]
        messages.reverse()
        if count > len(messages):
            # if ctx.author.id == 578006934507094016: return await ctx.send(len(messages)
            return await ctx.send("That snipe number is too high!", delete_after=5)
        message = self.edited[ctx.channel.id][count - 1].split("ß")
        embed = discord.Embed(
            description=f"{message[2]} **->** {message[3]}",
            colour=discord.Colour.random(),
            timestamp=datetime.datetime.fromtimestamp(int(message[1])),
        )
        sender: discord.User = await self.bot.fetch_user(int(message[0]))
        embed.set_author(name=str(sender), icon_url=sender.avatar.url)
        await ctx.send(embed=embed, delete_after=10)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return
        if message.content.lower() in cant:
            return
        try:
            if not self.messages[message.channel.id]:
                self.messages[message.channel.id] = []
        except KeyError:
            self.messages[message.channel.id] = []
        current_list: list = self.messages[message.channel.id]
        current_list.append(f"{message.author.id}ß{int(time.time())}ß{message.content}")

        self.messages[message.channel.id] = current_list

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return
        try:
            if not self.edited[before.channel.id]:
                self.edited[before.channel.id] = []
        except KeyError:
            self.edited[before.channel.id] = []
        current_list: list = self.edited[before.channel.id]
        current_list.append(
            f"{before.author.id}ß{int(time.time())}ß{before.content}ß{after.content}"
        )

        self.edited[before.channel.id] = current_list


async def setup(bot):
    await bot.add_cog(Snipe(bot))
