import traceback

import discord
from discord.ext import commands


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            1, 10, commands.BucketType.member
        )

    def get_command_signature(self, command: commands.Command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = "|".join(command.aliases)
            fmt = f"^{command.name}|{aliases}"
            if parent:
                fmt = f"{parent} {fmt}"
            alias = fmt
        else:
            alias = command.name if not parent else f"{parent} {command.name}"
        return f"```xml\n<{alias}: {command.signature} >```\n"

    async def send_command_help(self, ctx: commands.Context, command: commands.Command):
        embed = discord.Embed(colour=0xFF00FF)
        embed.set_footer(
            text=f"{str(self.bot.user.name)} help", icon_url=ctx.guild.icon.url
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
        self.common_command_formatting(embed, command)
        await ctx.send(embed=embed)

    def common_command_formatting(
        self, embed: discord.Embed, command: commands.Command
    ):
        embed.description = self.get_command_signature(command)
        if command.description:
            embed.description += (
                f"```ansi\n{command.description}\n\n{command.help}\n```"
            )
        else:
            embed.description += (
                "```ansi\n" + command.help + "\n```" or "No help found..."
            )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, exc):
        if isinstance(exc, discord.ext.commands.MissingRequiredArgument):
            await self.send_command_help(ctx, ctx.command)
        elif isinstance(exc, discord.ext.commands.MessageNotFound):
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
                    description=f"{exc.args[0]}", colour=discord.Colour.red()
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
