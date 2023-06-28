import asyncio
import re
import typing
from io import BytesIO

import PIL.Image
import discord  # noqa
import matplotlib.colors
from discord.ext import commands  # noqa

from modules.booster_redis import Boosters


class Dropdown(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(
                label="Colour",
                description="Change the colour of your role.",
                emoji="🌈",
                value="color",
            ),
            discord.SelectOption(
                label="Name",
                description="Change the name of your role.",
                emoji="💬",
                value="name",
            ),
            # discord.SelectOption(
            #     label="Icon",
            #     description="Change the emoji/image of your role.",
            #     emoji="🖼️",
            #     value="icon",
            # ),
            discord.SelectOption(
                label="Hoist",
                description="Toggle whether your role is hoisted.",
                emoji="📌",
                value="hoist",
            ),
            discord.SelectOption(
                label="Delete",
                description="Delete your custom role.",
                emoji="❌",
                value="delete",
            ),
        ]

        super().__init__(
            placeholder="Select an option.", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await Booster.callback(self.bot, interaction, self.values[0])


class DropDownView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=20)
        self.owner: typing.Union[int, None] = None
        self.message: typing.Union[discord.Message, None] = None
        self.add_item(Dropdown(bot))

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        self.stop()

    @discord.ui.button(label="Close Menu", style=discord.ButtonStyle.red)
    async def close(
        self, interaction: discord.Interaction, button: discord.ui.Button  # noqa
    ):
        await interaction.response.defer()
        await self.on_timeout()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.owner != interaction.user.id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"You can't use this menu. It's "
                    f"intended for <@{self.owner}>.",
                    colour=0xFF0000,
                ),
                ephemeral=True,
            )
            return False
        return True


class Confirm(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=10)
        self.owner: typing.Union[int, None] = None
        self.bot = bot
        self.value = False
        self.message: typing.Union[discord.Message, None] = None

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label="Delete Role", style=discord.ButtonStyle.red)
    async def close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):  # noqa
        await interaction.response.send_message("Deleting role...")
        self.value = True
        await self.on_timeout()
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.owner != interaction.user.id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"You can't use this menu. It's "
                    f"intended for <@{self.owner}>.",
                    colour=0xFF0000,
                ),
                ephemeral=True,
            )
            return False
        return True


class Booster(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.duck_guild: discord.Guild = bot.get_guild(790774812690743306)

    @commands.Cog.listener()
    async def on_ready(self):
        users_not_in_cache = [
            member.id
            for member in self.duck_guild.get_role(int(1121175332205101097)).members
        ]
        users_not_in_cache.extend(
            [
                member.id
                for member in self.duck_guild.get_role(int(888578948445900831)).members
            ]
        )
        users_not_in_cache.extend(
            [
                member.id
                for member in self.duck_guild.get_role(int(870049849414942771)).members
            ]
        )
        users_not_in_cache.extend(
            [
                member.id
                for member in self.duck_guild.get_role(int(1122596775077875832)).members
            ]
        )
        for key, value in Boosters.cache.copy().items():
            if not value:
                try:
                    users_not_in_cache.remove(key)
                except ValueError:
                    pass
                continue
            role: discord.Role = self.duck_guild.get_role(int(value))
            if not role:
                continue
            if len(role.members) < 1:
                await Boosters.delete(key)
                await role.delete(reason="Owner no longer in guild.")
                continue
            users_not_in_cache.remove(key)
        for user_id in users_not_in_cache:
            await Boosters.insert(user_id, None)

    @staticmethod
    async def callback(
        bot: commands.Bot, interaction: discord.Interaction, option: str
    ) -> discord.Embed:
        try:
            role_id = Boosters.cache[interaction.user.id]
        except KeyError:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"You don't have a custom role.", colour=0xFF0000
                )
            )
            return discord.Embed(
                description="You don't have a custom role.", colour=0xFF0000
            )
        if option == "color":
            return await Booster.edit_color(
                bot, interaction, interaction.guild.get_role(role_id)
            )
        elif option == "name":
            return await Booster.edit_name(
                bot, interaction, interaction.guild.get_role(role_id)
            )
        elif option == "icon":
            return await Booster.edit_icon_or_emoji(
                bot, interaction, interaction.guild.get_role(role_id)
            )
        elif option == "delete":
            return await Booster.delete(
                bot, interaction, interaction.guild.get_role(role_id)
            )
        elif option == "hoist":
            return await Booster.hoist(
                bot, interaction, interaction.guild.get_role(role_id)
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Invalid option: {option}. "
                    f"Please contact the Bot Dev Team "
                    f"for support!",
                    colour=0xFF0000,
                )
            )
            return Booster.generate_embed(interaction.guild.get_role(role_id))

    @staticmethod
    async def edit_icon_or_emoji(
        bot: commands.Bot, interaction: discord.Interaction, role: discord.Role
    ):
        await interaction.response.defer()
        if not role:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"You don't have a custom role.", colour=0xFF0000
                )
            )
            return

        def check():
            def inner_check(_message):
                return (
                    _message.author.id == interaction.user.id
                    and _message.channel.id == interaction.channel.id
                )

            return inner_check

        await interaction.channel.send(
            embed=discord.Embed(
                description=f"Please send the new icon or emoji for your custom role. \n\n"
                f"Please note, the emoji must be from **this server** or a default emoji. Discord does "
                f"not support animated emojis at this time.",
                colour=role.colour,
            )
        )
        try:
            file_emoji: discord.Message = await bot.wait_for(
                "message", check=check(), timeout=30
            )
        except asyncio.TimeoutError:
            await interaction.channel.send(
                embed=discord.Embed(
                    description=f"{interaction.user.mention}, you took too long to respond."
                    f" Please re-run the command.",
                    colour=0xFF0000,
                ),
                mention_author=False,
            )
            return

        if not file_emoji.attachments:
            emojis = re.findall(
                "<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>",
                file_emoji.content,
            )
            if not emojis:
                file = file_emoji.content.split(" ")[0]
            else:
                async with bot.session.get(  # type: ignore
                    [
                        x
                        for x in interaction.guild.emojis
                        if x.name.lower() == emojis[0][1]
                    ][0].url
                ) as response:
                    if response.status != 200:
                        await interaction.channel.send(
                            embed=discord.Embed(
                                description=f"{interaction.user.mention}, the emoji you provided is not a valid emoji.",
                                colour=0xFF0000,
                            ),
                            mention_author=False,
                        )
                        return
                    file = Booster.make_response_into_bytes(await response.read())
        else:
            url = file_emoji.attachments[0].url
            async with bot.session.get(url) as response:  # type: ignore
                if response.status != 200:
                    await interaction.channel.send(
                        embed=discord.Embed(
                            description=f"{interaction.user.mention}, there was an error with your request. "
                            f"Please try again.",
                            colour=0xFF0000,
                        ),
                        mention_author=False,
                    )
                    return
                else:
                    file = Booster.make_response_into_bytes(await response.read())
        if not file:
            await interaction.channel.send(
                embed=discord.Embed(
                    description=f"{interaction.user.mention}, There was an error getting your file/emoji. "
                    f"Please try again.",
                    colour=0xFF0000,
                ),
                mention_author=False,
            )
            return

        try:
            await role.edit(display_icon=file, reason="Role icon edited by user")
        except discord.HTTPException:
            await interaction.channel.send(
                embed=discord.Embed(
                    description=f"{interaction.user.mention}, there was an error with your request. "
                    f"Please try using a different emoji or a smaller image.",
                    colour=0xFF0000,
                ),
                mention_author=False,
            )
            return
        await interaction.channel.send(
            embed=discord.Embed(
                description=f"{interaction.user.mention}, your role icon has been updated.",
                colour=0x00FF00,
            ),
            mention_author=False,
        )
        return Booster.generate_embed(role)

    @staticmethod
    async def edit_color(
        bot: commands.Bot,
        interaction: discord.Interaction,
        role: typing.Union[discord.Role, None],
    ):
        await interaction.response.defer()
        if not role:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"You don't have a custom role.", colour=0xFF0000
                )
            )
            return

        def check():
            def inner_check(_message):
                return (
                    _message.author.id == interaction.user.id
                    and _message.channel.id == interaction.channel.id
                )

            return inner_check

        await interaction.channel.send(
            embed=discord.Embed(
                description=f"Please send a new colour for your "
                f"role. Use `None` if you want to clear "
                f"the colour.",
                colour=role.colour,
            ),
        )
        try:
            color: discord.Message = await bot.wait_for(
                "message", check=check(), timeout=45
            )
        except asyncio.TimeoutError:
            await interaction.channel.send(
                embed=discord.Embed(
                    description=f"{interaction.user.mention}, you took too long to respond."
                    f" Please re-run the command.",
                    colour=0xFF0000,
                ),
                mention_author=False,
            )
            return

        if color.content.lower() != "none":
            if color.content[0] != "#":
                color.content = "#" + color.content
            try:
                thy_color = await commands.ColourConverter().convert(
                    interaction, argument=color.content  # type: ignore
                )
            except commands.BadArgument:
                try:
                    thy_color = int(
                        matplotlib.colors.cnames[
                            color.content.lower().replace("#", "").replace(" ", "")
                        ].replace("#", ""),
                        16,
                    )
                except KeyError:
                    await interaction.channel.send(
                        embed=discord.Embed(
                            description=f"{interaction.user.mention}, that's not a valid colour. "
                            f"Please re-run this command to try again.\nUse "
                            f"[this](https://htmlcolorcodes.com/color-picker/ "
                            f'"RGB Color Picker") link to pick a colour.',
                            colour=0xFF0000,
                        ),
                        mention_author=True,
                    )
                    return
        else:
            thy_color = 0
        await role.edit(colour=thy_color, reason="Custom role colour edited.")
        await interaction.channel.send(
            embed=discord.Embed(
                description=f"Successfully edited the colour of " f"{role.mention}.!",
                colour=role.colour,
            )
        )
        return Booster.generate_embed(role)

    @staticmethod
    async def edit_name(
        bot: commands.Bot,
        interaction: discord.Interaction,
        role: typing.Union[discord.Role, None],
    ):
        await interaction.response.defer()
        if not role:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"You don't have a custom role.", colour=0xFF0000
                )
            )
            return

        def check():
            def inner_check(_message):
                return (
                    _message.author.id == interaction.user.id
                    and _message.channel.id == interaction.channel.id
                )

            return inner_check

        await interaction.channel.send(
            embed=discord.Embed(
                description=f"Please send a new name for your " f"role.",
                colour=role.colour,
            )
        )
        try:
            message: discord.Message = await bot.wait_for(
                "message", check=check(), timeout=30
            )
        except asyncio.TimeoutError:
            await interaction.channel.send(
                embed=discord.Embed(
                    description=f"{interaction.user.mention}, you took too long to respond."
                    f" Please re-run the command.",
                    colour=0xFF0000,
                ),
                mention_author=False,
            )
            return

        if len(message.content) < 2 or len(message.content) > 32:
            await interaction.channel.send(
                embed=discord.Embed(
                    description=f"Your custom role name must be "
                    f"inbetween 2 and "
                    f"32 "
                    f"characters. ({len(message.content)})",
                    colour=0xFF0000,
                ),
                mention_author=True,
            )
            return
        if message.content.lower() in [
            role.name.lower() for role in interaction.guild.roles
        ]:
            await interaction.channel.send(
                embed=discord.Embed(
                    description=f"A role with that name already exists. "
                    f"Please re-run this command to try again.",
                    colour=0xFF0000,
                ),
                mention_author=True,
            )
            return
        old_name = role.name
        await role.edit(name=message.content, reason="Custom role colour edited.")
        await interaction.channel.send(
            interaction.user.mention,
            embed=discord.Embed(
                description=f"Successfully edited the name of your role!\n{old_name} -> {role.name}!",
                colour=role.colour,
            ),
        )
        return Booster.generate_embed(role)

    @staticmethod
    async def delete(
        bot: commands.Bot,
        interaction: discord.Interaction,
        role: typing.Union[discord.Role, None],
    ):
        await interaction.response.defer()
        if role is None:
            await interaction.channel.send(
                embed=discord.Embed(
                    description=f"You do not have a custom role.", colour=0xFF0000
                ),
                mention_author=True,
            )
            return

        view = Confirm(bot)
        view.owner = interaction.user.id

        view.message = await interaction.channel.send(
            f"{interaction.user.mention}",
            embed=discord.Embed(
                description=f"Are you sure you want to delete your custom role?"
            ),
            view=view,
        )
        await view.wait()
        if view.value:
            await interaction.channel.send(
                embed=discord.Embed(
                    description=f"Successfully deleted the custom role `{role.name}`."
                )
            )
            await role.delete(reason="Custom role deleted.")
        return discord.Embed(description="Goodbye!", colour=discord.Colour.green())

    @commands.command(aliases=["br", "boosterrole"])
    # booster | staff team | level 20
    @commands.has_any_role(
        870049849414942771, 888578948445900831, 1121175332205101097, 1122596775077875832
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def custom_role(self, ctx: commands.Context) -> None:
        try:
            role_id = Boosters.cache[ctx.author.id]
        except KeyError:
            role_id = 0
        if not ctx.guild.get_role(role_id):
            role = await self.setup_custom_role(ctx)
            if not role:
                return
            role_id = role.id
        role = discord.utils.get(ctx.guild.roles, id=role_id)
        view = DropDownView(self.bot)
        view.owner = ctx.author.id
        view.message = await ctx.reply(embed=self.generate_embed(role), view=view)
        await view.wait()  # Prevents the command from being executed until the user has selected an option.

    async def setup_custom_role(
        self, ctx: commands.Context
    ) -> typing.Union[discord.Role, None]:
        def check():
            def inner_check(_message):
                return (
                    _message.author == ctx.author
                    and _message.channel.id == ctx.channel.id
                )

            return inner_check

        embed = discord.Embed(
            description=f"{ctx.author.mention}, We thank you for boosting our server! "
            f"<a:scoldsoncrackhelp:1115303711963623494>\n\nTo setup your "
            f"custom role, please send the role of your name in chat now.",
            color=0xF47FFF,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text=f"{str(ctx.author)} - {ctx.author.id}")
        await ctx.reply(embed=embed)
        try:
            message: discord.Message = await self.bot.wait_for(
                "message", check=check(), timeout=30
            )
        except asyncio.TimeoutError:
            await ctx.reply(
                embed=discord.Embed(
                    description=f"{ctx.author.mention}, you took too long to respond. "
                    f"Please re-run the command.",
                    colour=0xFF0000,
                ),
                mention_author=False,
            )
            return
        if len(message.content) < 2 or len(message.content) > 32:
            await ctx.reply(
                embed=discord.Embed(
                    description=f"Your custom role name must be "
                    f"inbetween 2 and 32 "
                    f"characters. ({len(message.content)})",
                    colour=0xFF0000,
                ),
                mention_author=True,
            )
            return
        if message.content.lower() in [role.name.lower() for role in ctx.guild.roles]:
            await ctx.reply(
                embed=discord.Embed(
                    description=f"A role with that name already exists. "
                    f"Please re-run this command to try again.",
                    colour=0xFF0000,
                ),
                mention_author=True,
            )
            return
        await ctx.reply(
            embed=discord.Embed(
                description=f"Alright, {ctx.author.mention}, you decided to use "
                f"**{message.content}** as your custom role name. "
                f"Now send a colour in chat! Send `None` if you don't want a "
                f"colour.",
                colour=0xF47FFF,
            ),
            mention_author=True,
        )

        try:
            color: discord.Message = await self.bot.wait_for(
                "message", check=check(), timeout=45
            )
        except asyncio.TimeoutError:
            await ctx.reply(
                embed=discord.Embed(
                    description=f"{ctx.author.mention}, you took too long to respond. "
                    f"Please re-run the command.",
                    colour=0xFF0000,
                ),
                mention_author=False,
            )
            return
        if color.content.lower() != "none":
            if color.content[0] != "#":
                color.content = "#" + color.content
            try:
                thy_color = await commands.ColourConverter().convert(
                    ctx, argument=color.content
                )
            except commands.BadArgument:
                try:
                    thy_color = int(
                        matplotlib.colors.cnames[
                            color.content.lower().replace("#", "").replace(" ", "")
                        ].replace("#", ""),
                        16,
                    )
                except KeyError:
                    await ctx.reply(
                        embed=discord.Embed(
                            description=f"{ctx.author.mention}, that's not a valid colour. "
                            f"Please re-run this command to try again.\nUse "
                            f"[this](https://htmlcolorcodes.com/color-picker/ "
                            f'"RGB Color Picker") link to pick a colour. Or input a color by it\'s name.',
                            colour=0xFF0000,
                        ),
                        mention_author=True,
                    )
                    return
        else:
            thy_color = None
        await ctx.send(
            embeds=[
                discord.Embed(
                    description=f"Alright, {ctx.author.mention}, you decided to use"
                    f" **{message.content}** as your custom role name, and you "
                    f"decided to use **{str(thy_color).upper()}** as your "
                    f"custom role colour",
                    colour=thy_color,
                ),
                discord.Embed(
                    description=f"If you want to ever change your custom role name / colour "
                    f"or to assign an emoji / picture to it, "
                    f"just re-run this command!",
                    colour=0xF47FFF,
                ),
            ]
        )
        edit_me = await ctx.send("Please wait a bit :)")
        try:
            _role = await ctx.guild.create_role(
                name=message.content,
                colour=thy_color,
                reason=f"Created by {str(ctx.author)} for boosting.",
                mentionable=False,
                hoist=False,
            )
            await asyncio.sleep(1)
            role_pos = ctx.guild.get_role(1023271818271932428)
            if not role_pos:
                await ctx.send(
                    embed=discord.Embed(
                        description=f"An error occurred. The custom role threshold role "
                        f"doesn't exist. Please contact a staff member.",
                        colour=0xFF0000,
                    )
                )
                await _role.delete(reason="Deleted due to an error.")
                return
            await _role.edit(
                position=role_pos.position + 1,
                reason=f"Edited by {str(ctx.author)} for boosting.",
            )
            await asyncio.sleep(2)
            await ctx.author.add_roles(
                _role, reason=f"Created by {str(ctx.author)} for boosting."
            )
            await Boosters.insert(ctx.author.id, _role.id)
        except discord.DiscordException as e:
            print(e)
            await asyncio.sleep(1)
            await edit_me.edit(
                content=f"An error occurred. Please recheck your inputted values and try again."
            )
            return
        await edit_me.edit(
            content=f"Successfully created a custom role for {ctx.author.mention}. {_role.mention}!"
        )

        return _role

    @staticmethod
    def generate_embed(role: discord.Role) -> discord.Embed:
        embed = discord.Embed(
            description=f"The name of your custom role is currently **`{role.name}`** "
            f"({role.mention}).\n"
            f"The hex is {str(role.colour).upper()}\n\n"
            f"",
            colour=role.colour,
            timestamp=role.created_at,
        )
        if role.icon:
            embed.set_thumbnail(url=role.icon.url)
        elif role.unicode_emoji:
            embed.description += "The emoji for this role is `{}`".format(
                role.unicode_emoji
            )
        else:
            pass
        embed.set_footer(text=f"Role created on ")
        return embed

    @commands.Cog.listener()
    async def on_member_update(self, _: discord.Member, after: discord.Member):
        allowed_roles = [
            after.get_role(1121175332205101097),
            after.get_role(870049849414942771),
            after.get_role(888578948445900831),
            after.get_role(1122596775077875832),
        ]
        for role in allowed_roles:
            if role in after.roles:
                if after.id not in Boosters.cache.keys():
                    await Boosters.insert(after.id, None)
                return
        if after.id in Boosters.cache.keys():
            await self.delete_custom_role(after.guild, Boosters.cache[after.id])
            await Boosters.delete(after.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.id in Boosters.cache.keys():
            await self.delete_custom_role(member.guild, Boosters.cache[member.id])
            await Boosters.delete(member.id)

    @staticmethod
    async def delete_custom_role(guild: discord.Guild, role_id):
        if role_id is not None:
            role = guild.get_role(role_id)
            if role is not None:
                try:
                    await role.delete(reason="Boost ended")
                except discord.DiscordException as e:
                    print(str(e))

    @staticmethod
    def make_response_into_bytes(response: bytes) -> bytes:
        img = PIL.Image.open(BytesIO(response))
        img = img.resize((64, 64), PIL.Image.ANTIALIAS)
        file = BytesIO()
        img.save(file, "png")
        file.seek(0)
        return bytes(file.read())

    @staticmethod
    async def hoist(bot, interaction, param: discord.Role):
        if param.hoist:
            await param.edit(hoist=False)
            await interaction.response.send_message(
                f"Successfully unhoisted {param.mention}!", ephemeral=True
            )
        else:
            await param.edit(hoist=True)
            await interaction.response.send_message(
                f"Successfully hoisted {param.mention}!", ephemeral=True
            )
        return discord.Embed()


async def setup(bot):
    await bot.add_cog(Booster(bot))
