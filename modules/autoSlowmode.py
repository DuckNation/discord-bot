from typing import Optional

from discord.ext import commands
import discord
from discord.ext.commands import has_permissions


class AutoSlowmode(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.channels = {}

    # @commands.command()
    # @has_permissions(administrator=True)
    # async def channel_add(self, ctx: commands.Context, channel: Optional[discord.TextChannel]):
    #     if not channel:
    #         channel = ctx.channel
    #
    #     self.channels.


async def setup(bot):
    await bot.add_cog(AutoSlowmode(bot))
