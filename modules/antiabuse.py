import time

import discord
from discord.ext import commands


class Abuse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.is_timed_out():
            return
        async for entry in before.guild.audit_logs(limit=2, action=discord.AuditLogAction.member_update):
            if entry.target == after:
                if isinstance(entry.reason, str):
                    if len(entry.reason) > 4:
                        return
                await after.edit(timed_out_until=None, reason="Supply a reason longer than 5 characters.")


async def setup(bot):
    await bot.add_cog(Abuse(bot))
