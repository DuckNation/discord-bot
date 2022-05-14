import asyncio
import json
import time
import typing

import discord
import pymongo
from bson import ObjectId
from discord.ext import commands
from discord.ext.commands import BucketType
from pymongo.collection import Collection
from pymongo.results import InsertOneResult

from modules.utils import embeds


async def get_info_embed(guild: discord.Guild, **kwargs) -> discord.Embed:
    default_kwargs = {
        "_id": None,
        "owner_id": None,
        "creation": int(time.time()),
        "member_count": 1,
        "staff": [],
        "voice_chat": None,
        "description": "No description provided...",
    }
    kwargs = default_kwargs | kwargs
    staff_members = [
        "> " + str(guild.get_member(int(x))) + "\n" for x in kwargs.pop("staff")
    ]
    embed = discord.Embed(
        description=f"**Community Information**\n\n"
        f"Owner: <@{kwargs.get('owner_id')}> {str(guild.get_member(int(kwargs.pop('owner_id'))))}\n"
        f"Description: {kwargs.pop('description')}\n"
        f"Member Count: {kwargs.pop('member_count')}\n"
        f"Voice: {kwargs.pop('voice_chat')}\n"
        f"Created: <t:{kwargs.pop('creation')}>\n"
        f"\nStaff:\n{''.join(staff_members)}",
        color=discord.Colour.brand_green(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text=f"Community ID: {kwargs.pop('_id')}")
    return embed


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

    async def get_community_by_owner_id(self, discord_id: typing.Union[str, int]):
        return (
            await self.db.get_database("duckServer")
            .get_collection("communities")
            .find_one({"owner_id": str(discord_id)})
        )

    async def get_community_by_channel_id(self, channel_id: typing.Union[str, int]):
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

    async def get_community_by_id(self, community_id: str):
        return (
            await self.db.get_database("duckServer")
            .get_collection("communities")
            .find_one({"_id": ObjectId(community_id)})
        )

    async def get_community_somehow(
        self, guild: discord.Guild, *, searchable: typing.Union[str, int]
    ):
        searchable = (
            str(searchable)
            .replace(" ", "")
            .lower()
            .replace("<", "")
            .replace(">", "")
            .replace("#", "")
            .replace("@", "")
            .replace("!", "")
        )
        _type = None
        if len(str(searchable)) == 18:
            if guild.get_channel(int(searchable)):
                _type = "channel_id"
            elif guild.get_member(int(searchable)):
                _type = "owner_id"
            else:
                _type = None
        elif len(str(searchable)) == 24:
            _type = "community_id"
        else:
            _type = None

        if _type:
            if _type == "channel_id":
                return await self.get_community_by_channel_id(searchable)
            if _type == "owner_id":
                return await self.get_community_by_owner_id(searchable)
            if _type == "community_id":
                return await self.get_community_by_id(searchable)
        else:
            return await self.get_community_by_exact_name(
                searchable.replace(" ", "-").lower()
            )
        return None

    async def get_community_info(
        self, guild: discord.Guild, search_by: typing.Union[str, int]
    ) -> typing.Union[discord.Embed, None]:
        community = await self.get_community_somehow(guild, searchable=search_by)
        if not community:
            return None
        return await get_info_embed(
            guild,
            _id=community["_id"],
            owner_id=community["owner_id"],
            creation=community["creation"],
            member_count=community["member_count"],
            staff=community["moderators"],
            voice_chat=community["voice_chat"],
            description=community["description"],
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
            "**add**: Add someone to your community.\n"
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

    @community.group(aliases=["a"])
    @commands.is_owner()
    async def admin(self, ctx: commands.Context):
        pass

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
            ),  # owner
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
            ctx.guild.get_role(926905864701493258): discord.PermissionOverwrite(
                send_messages=False,
                add_reactions=False,
                create_public_threads=False,
                create_private_threads=False,
                send_messages_in_threads=False,
            ),  # muted
        }
        message = await ctx.send(embed=first)
        channel = await ctx.guild.get_channel(887858173942308914).create_text_channel(
            name=name,
            overwrites=overwrites,
            topic=f"{str(ctx.author)}'s awesome community.",
        )
        members = channel.members
        real_members = [x.id for x in members if not x.bot]
        channel_thing = await channel.send(content="holder")

        a: InsertOneResult = await self.col.insert_one(
            {
                "owner_id": str(ctx.author.id),
                "channel_id": str(channel.id),
                "message_id": str(channel_thing.id),
                "creation": int(time.time()),
                "member_count": len(real_members),
                "name": str(channel.name),
                "moderators": [],
                "voice_chat": None,
                "banned_members": [],
                "settings": {},
                "description": f"{str(ctx.author)}'s awesome community!",
            }
        )

        e = await get_info_embed(
            ctx.guild, owner_id=ctx.author.id, _id=a.inserted_id, staff=real_members
        )
        await channel_thing.edit(embed=e, content=None)
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
    @commands.cooldown(1, 20, BucketType.user)
    async def join(self, ctx: commands.Context, *, searchable: typing.Union[str, int]):
        """
        Join a community using the owner ID, channel ID, or the name
        """
        community = await self.get_community_somehow(ctx.guild, searchable=searchable)
        if not community:
            return await ctx.send(
                embed=embeds.get_error_embed("A community wasn't found by that query!")
            )
        if str(ctx.author.id) in community["banned_members"]:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    f"You are not permitted to join {community['name']}!"
                )
            )
        channel = ctx.guild.get_channel(int(community["channel_id"]))
        overwrites = channel.overwrites
        if ctx.author in overwrites:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    f"You've already joined <#{community['channel_id']}>!"
                )
            )

        overwrites[ctx.author] = discord.PermissionOverwrite(read_messages=True)
        await channel.edit(overwrites=overwrites)
        await ctx.send(
            embed=discord.Embed(
                description=f"Added you to {community['name']}!",
                color=discord.Colour.green(),
                timestamp=discord.utils.utcnow(),
            )
        )

    @community.command()
    @commands.cooldown(1, 20, BucketType.user)
    async def leave(
        self,
        ctx: commands.Context,
        *,
        searchable: typing.Optional[typing.Union[str, int]],
    ):
        """
        Leave a community by running it in the channel or by using the owner ID, channel ID, or the name
        """
        if not searchable:
            searchable = str(ctx.channel.id)
        community = await self.get_community_somehow(ctx.guild, searchable=searchable)
        if not community:
            return await ctx.send(
                embed=embeds.get_error_embed("A community wasn't found by that query!")
            )
        if str(ctx.author.id) == community["owner_id"]:
            return await ctx.send(
                embed=embeds.get_error_embed("You can't leave a community you own!")
            )
        channel = ctx.guild.get_channel(int(community["channel_id"]))
        overwrites = channel.overwrites
        if ctx.author not in overwrites:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    f"You're not in <#{community['channel_id']}>!"
                )
            )

        await ctx.send(
            embed=discord.Embed(
                description=f"Removed you from {community['name']}!",
                color=discord.Colour.green(),
                timestamp=discord.utils.utcnow(),
            )
        )
        await channel.set_permissions(ctx.author, overwrite=None)

    @community.command()
    @commands.cooldown(1, 20, BucketType.user)
    async def add(
        self,
        ctx: commands.Context,
        members: commands.Greedy[discord.Member],
        *,
        searchable: typing.Union[str, int] = None,
    ):
        """
        Adds multiple members to your community.

        Parameters:
        members, channel

        If a channel isn't specified, defaults to the channel it was executed in.

        Example:
        community add haappi haappiv2 haappiv3 genshin-impact
        """
        if searchable:
            search_string = searchable
        else:
            search_string = ctx.author.id
        community = await self.get_community_somehow(
            ctx.guild, searchable=search_string
        )
        if not community:
            return await ctx.send(
                embed=embeds.get_error_embed("You don't own a community!")
            )

    @admin.command()
    @commands.cooldown(1, 10, BucketType.default)
    async def find_raw(
        self, ctx: commands.Context, *, searchable: typing.Union[str, int]
    ):
        """
        Locate a community by a query. Dumps raw JSON, use `community admin find` instead.
        """
        community = await self.get_community_somehow(ctx.guild, searchable=searchable)
        if community:
            return await ctx.send(community)
        return await ctx.send(
            embed=embeds.get_error_embed(
                f"A community wasn't found by the query of {searchable}"
            )
        )

    @admin.command()
    @commands.cooldown(1, 15, BucketType.default)
    async def find(
        self,
        ctx: commands.Context,
        *,
        searchable: typing.Optional[typing.Union[str, int]],
    ):
        """
        Locate a community by either a <name | owner_id | channel_id | community_id | voice_channel>

        Shows extra information. Recommended not to run in public channels
        """
        if not searchable:
            searchable = ctx.channel.id
        embed = await self.get_community_info(ctx.guild, search_by=searchable)
        if not embed:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    "A community wasn't found with that query!"
                )
            )
        community = await self.get_community_somehow(ctx.guild, searchable=searchable)

        embed.description += f"\n\n**Staff Fields**\nCustom Settings: {json.dumps((community['settings']), indent=2)}\n"
        return await ctx.send(embed=embed)

    @admin.command(aliases=["create"])
    @commands.cooldown(1, 30, BucketType.default)
    async def admin_create(self, ctx: commands.Context, owner: discord.Member):
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
                    f"This community already has an owner! <@{exists['owner_id']}> ({exists['owner_id']}). It was "
                    f"created on <t:{exists['creation']}>"
                )
            )
        message = await ctx.send("a")
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
                "message_id": str(message.id),
                "description": f"{str(owner)}'s awesome community.",
            }
        )
        self.__name_cache[str(ctx.channel.name)] = ctx.channel.id
        await ctx.send(
            embed=discord.Embed(
                description=f"{str(owner)} now owns this community.",
                color=discord.Colour.green(),
            )
        )

    @admin.command()
    @commands.cooldown(1, 30, BucketType.default)
    async def transfer(
        self, ctx: commands.Context, new_owner: discord.Member, *, query: str = None
    ):
        """
        Transfers a community to another user
        """
        if not query:
            query = ctx.channel.id
        community = await self.get_community_somehow(ctx.guild, searchable=str(query))
        if not community:
            return await ctx.send(
                embed=embeds.get_error_embed(
                    "A community wasn't found with that query!"
                )
            )
        if community["owner_id"] == str(new_owner.id):
            return await ctx.send(
                embed=embeds.get_error_embed(
                    f"{new_owner.mention} already owns this community!"
                )
            )
        await self.col.delete_one({"_id": ObjectId(community["_id"])})
        await self.admin_create(ctx, new_owner)


async def setup(bot):
    await bot.add_cog(Community(bot))
