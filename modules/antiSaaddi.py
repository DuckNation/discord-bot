from discord.ext import commands
import discord


class AntiSaaddi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.author.bot:
            return
        if 'saaddi' in message.content.lower():
            await message.delete()


async def setup(bot):
    await bot.add_cog(AntiSaaddi(bot))
