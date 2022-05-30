from discord.ext import commands
import discord


class AntiSaaddi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            return
        if message.content.lower().contains('saaddi'):
            await message.delete()


async def setup(bot):
    await bot.add_cog(AntiSaaddi(bot))
