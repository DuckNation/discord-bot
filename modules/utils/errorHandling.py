import traceback

import discord
from discord.ext import commands


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            1, 10, commands.BucketType.member
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, exc):
        if isinstance(exc, discord.ext.commands.MessageNotFound):
            e = discord.Embed(
                description=f" I couldn't find that message",
                colour=discord.Colour.red(),
            )
            await ctx.send(embed=e)
        elif isinstance(exc, discord.ext.commands.MemberNotFound):
            e = discord.Embed(
                description=f" I couldn't find that member",
                colour=discord.Colour.red(),
            )
            await ctx.send(embed=e)
        elif isinstance(exc, discord.ext.commands.ChannelNotFound):
            e = discord.Embed(
                description=f" I couldn't find that channel",
                colour=discord.Colour.red(),
            )
            await ctx.send(embed=e)
        elif isinstance(exc, discord.ext.commands.RoleNotFound):
            e = discord.Embed(
                description=f" I couldn't find that role",
                colour=discord.Colour.red(),
            )
            await ctx.send(embed=e)
        elif isinstance(exc, discord.ext.commands.EmojiNotFound):
            e = discord.Embed(
                description=f" I couldn't find that emoji",
                colour=discord.Colour.red(),
            )
            await ctx.send(embed=e)
        elif isinstance(exc, discord.ext.commands.NotOwner):
            e = discord.Embed(description=f"That command is only for bot owners")
            await ctx.send(embed=e, delete_after=5)
        elif isinstance(exc, discord.ext.commands.CommandOnCooldown):
            bucket = self.cd_mapping.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            if not retry_after:
                e = discord.Embed(
                    description=f"This command is on cooldown for another {int(exc.retry_after)} seconds!",
                    colour=discord.Colour.red(),
                )
                await ctx.send(embed=e, delete_after=int(exc.retry_after))

        elif isinstance(exc, discord.ext.commands.errors.BadArgument):
            return await ctx.send(
                embed=discord.Embed(
                    description="You sent a bad argument. Did you mean to view the "
                    "help page to view the correct command usage sMh?"
                )
            )
        elif isinstance(exc, discord.ext.commands.errors.CommandNotFound):
            pass
        else:

            etype = type(exc)
            trace = exc.__traceback__
            lines = traceback.format_exception(etype, exc, trace)
            traceback_text = "".join(lines)
            print(traceback_text)


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
