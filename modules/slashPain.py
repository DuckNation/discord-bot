from typing import Literal

from discord import app_commands
from discord.ext import commands
import discord


class SlashPain(commands.Cog):
    def __init__(self, bot):
        # super().__init__()
        self.bot: commands.Bot = bot

    @commands.command()
    async def load(self, ctx):
        await self.bot.tree.sync(guild=discord.Object(id=790774812690743306))
        await ctx.send("done")


@app_commands.context_menu(name="Delete Message")
async def info_menu(interaction: discord.Interaction, message: discord.Message):
    if interaction.user.id not in (821647232801570866, 578006934507094016):
        return await interaction.response.send_message("shoo")

    if (
        message.channel.id != 947182765990891530
        and message.author.id != 578006934507094016
    ):
        return await interaction.response.send_message("shoo")

    if message.guild.get_role(888578948445900831) in message.author.roles:
        return await interaction.response.send_message("shoo")
    await message.delete()
    await interaction.response.send_message("Deleted their message!")

    # @app_commands.command()
    # @app_commands.describe(fruits='fruits to choose from')
    # async def fruit(self, interaction: discord.Interaction, fruits: Literal['apple', 'banana', 'cherry']):
    #     await interaction.response.send_message(f'Your favourite fruit iaaaaaas {fruits}.')

    # @app_commands.context_menu()
    # async def example_user_context_menu(interaction: discord.Interaction, user: discord.Member):
    #     await interaction.response.send_message("fat")


async def setup(bot: commands.Bot):
    await bot.add_cog(SlashPain(bot))
    bot.tree.add_command(info_menu, guild=discord.Object(id=790774812690743306))
