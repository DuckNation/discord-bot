import pymongo
from discord.ext import commands
import discord


class InGameLinking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: pymongo.MongoClient = bot.db

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is not None:
            return

        if len(message.content) != 4:
            return

        try:
            int(message.content)
        except ValueError:
            return

        document = await self.bot.db.get_database("duckMinecraft").get_collection("playerData").find_one(
            {"pinCode": str(message.content)})
        if document is None:
            await message.channel.send("Invalid pin code!")
            return

        document["pinCode"] = None
        document["discordID"] = message.author.id

        await self.db.get_database("duckMinecraft").get_collection("playerData").update_one({'_id': document["_id"]},
                                                                                            {'$set': document})
        await message.channel.send(f"Linked to {document['playerName']}!")

        await self.db.get_database("duckMinecraft").get_collection("messages").insert_one(
            {
                "type": "discord_update",
                "bound": "serverbound",
                "uuid": document['_id'],
                "message": "<aqua>You have been linked the account <yellow>{}<aqua>!".format(document['playerName']),
            }
        )


async def setup(bot):
    await bot.add_cog(InGameLinking(bot))
