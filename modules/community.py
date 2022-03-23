import asyncio
import time
import typing
from inspect import Parameter
from typing import Optional

import pymongo
from discord.ext import commands
import discord
from discord.ext.commands import BucketType
from pymongo.collection import Collection

from modules.utils import embeds


class Community(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db: pymongo.MongoClient = bot.db
        self.col: Collection = self.db.get_database("duckServer").get_collection(
            "communities"
        )
        self.__name_cache = {}

    @commands.Cog.listener(name="on_ready")
    async def populate_name_cache(self):
        async for doc in self.col.find():
            self.__name_cache[doc["name"]] = int(doc["channel_id"])
            # self.__name_cache[doc['channel_id']] = (doc['name'])

    async def get_community_by_owner_id(self, discord_id: int):
        return (
            await self.db.get_database("duckServer")
            .get_collection("communities")
            .find_one({"owner_id": str(discord_id)})
        )

    async def get_community_by_channel_id(self, channel_id: int):
        return (
            await self.db.get_database("duckServer")
            .get_collection("communities")
            .find_one({"channel_id": str(channel_id)})
        )

    async def get_community_by_exact_name(self, name: str):
        return (
            await self.db.get_database("duckServer")
            .get_collection("communities")
            .find_one({"name": str(name)})
        )

    @commands.group(aliases=["c", "communities"], invoke_without_command=True)
    async def community(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Community Help",
            description="Communities are text-channels relating to any topic! "
            "Run `help community <sub command>` to view the full"
            " command usage!\n\n",
            color=discord.Colour.random(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text=f"{str(ctx.author)}")
        embed.description += (
            "Available subcommands-\n\n"
            "**create**: Creates a community.\n"
            "**edit**: Edit aspects of your community.\n"
            "**add**: Add someone to your community."
            "**list**: List all joinable communities.\n"
            "**join**: Join a community.\n"
            "**leave**: Leave a community,\n"
            "**search**: Search for a specific community.\n"
            "**info**: Lists info on a specific community.\n"
            "🔺 **delete**: Send a delete request in for your community.\n"
            "🔺 **transfer**: Transfers ownership to another member.\n"
            "🔺 **report**: Reports a community."
        )
        return await ctx.reply(embed=embed)

    @community.command()
    @commands.cooldown(1, 60, BucketType.user)
    async def create(self, ctx: commands.Context, *, name: str):
        """
        \u001b[0;36mCreates a community. You must have the \u001b[1;34mLevel 20 \u001b[0;36mrole to create one.

        Example:
        \u001b[0;1mcommunity create My Awesome Community!
        """
        community = await self.get_community_by_owner_id(ctx.author.id)
        if community:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    f"You already own a community at <#{community['channel_id']}>!"
                )
            )
        if ctx.guild.get_role(888106790192033792) not in ctx.author.roles:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    f"You cannot run this! You require the "
                    f"**<@&888106790192033792>** role!"
                )
            )
        if len(name) > 99:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    "The channel name must be less than 100 characters!"
                )
            )
        exists = await self.get_community_by_exact_name(name.lower().replace(" ", "-"))
        if exists:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    f"Another community by the name of `{name}` already " f"exists!"
                )
            )
        first = discord.Embed(
            description="Creating your channel...", color=discord.Colour.red()
        )
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                create_private_threads=True,
                create_public_threads=True,
                add_reactions=True,
                attach_files=True,
                embed_links=True,
                external_emojis=True,
                external_stickers=True,
                send_messages_in_threads=True,
                send_tts_messages=False,
                use_slash_commands=True,
            ),
            ctx.guild.get_role(888578948445900831): discord.PermissionOverwrite(
                read_messages=True, manage_messages=True, manage_threads=True
            ),  # staff team
            ctx.author: discord.PermissionOverwrite(
                read_messages=True, manage_messages=True, manage_threads=True
            ),
            ctx.guild.get_member(339254240012664832): discord.PermissionOverwrite(
                read_messages=True
            ),  # amari
            ctx.guild.get_member(292953664492929025): discord.PermissionOverwrite(
                read_messages=True
            ),  # unb
            ctx.guild.get_member(155149108183695360): discord.PermissionOverwrite(
                read_messages=True,
                manage_channels=True,
                manage_messages=True,
                manage_permissions=True,
            ),  # dyno
            ctx.guild.get_member(559426966151757824): discord.PermissionOverwrite(
                read_messages=True, manage_messages=True, manage_webhooks=True
            ),  # nqn
        }
        message = await ctx.send(embed=first)
        channel = await ctx.guild.get_channel(887858173942308914).create_text_channel(
            name=name,
            overwrites=overwrites,
            topic=f"{str(ctx.author)}'s awesome community.",
        )
        await self.col.insert_one(
            {
                "owner_id": str(ctx.author.id),
                "channel_id": str(channel.id),
                "creation": int(time.time()),
                "member_count": 1,
                "name": str(channel.name),
                "moderators": [],
                "voice_chat": None,
                "banned_members": [],
                "settings": {},
            }

        )
        self.__name_cache[str(channel.name)] = channel.id
        second = discord.Embed(
            description="Setting permissions...", color=discord.Colour.orange()
        )
        third = discord.Embed(description="Done!", color=discord.Colour.green())
        await message.edit(embeds=[first, second])
        await asyncio.sleep(2.5)
        await message.edit(embeds=[first, second, third])
        await ctx.send(
            f"{ctx.author.mention}, created your new community at {channel.mention}! <:duck_hearts:799084091809988618>"
        )

    @community.command()
    @commands.is_owner()  # todo refactor so its an admin command
    # https://stackoverflow.com/questions/50548316/subcommands-in-python-bot
    async def force_create(self, ctx: commands.Context, owner: discord.Member):
        """
        Force creates a community in the channel it's ran in with the owner.

        This is only useful if a community was made by hand, and is owner-less
        """
        if ctx.channel.category_id != 887858173942308914:
            return await ctx.send(
                embed=embeds.get_error_embed("This can't be ran here!")
            )
        if owner.bot:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    f"A bot can't be set as the community owner!"
                )
            )
        exists = await self.get_community_by_channel_id(ctx.channel.id)
        if exists:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    f"This community already has an owner! <@{exists['owner_id']}> ({exists['owner_id']}). It was created"
                    f" on <t:{exists['creation']}>"
                )
            )
        await self.col.insert_one(
            {
                "owner_id": str(owner.id),
                "channel_id": str(ctx.channel.id),
                "creation": int(ctx.channel.created_at.timestamp()),
                "member_count": 1,
                "name": str(ctx.channel.name),
                "moderators": [],
                "voice_chat": None,
                "banned_members": [],
                "settings": {},
            }
        )
        self.__name_cache[str(ctx.channel.name)] = ctx.channel.id
        await ctx.send(
            embed=discord.Embed(
                description=f"{str(owner)} now owns this community.",
                color=discord.Colour.green(),
            )
        )


async def setup(bot):
    await bot.add_cog(Community(bot))
