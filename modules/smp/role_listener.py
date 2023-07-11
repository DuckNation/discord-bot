import discord
from discord.ext import commands


def get_higher_roles(role_id):
    higher_roles = []
    for key, value in SMPListener.role_mapping.items():
        if key == role_id:
            break
        higher_roles.append(key)
    return higher_roles


def get_highest_level_role(roles: list[discord.Role]) -> discord.Role:
    highest_role = None
    roles = sorted(roles, key=lambda x: x.position, reverse=True)
    for role in roles:
        if role.id in SMPListener.role_mapping:
            highest_role = role
            break
    return highest_role


class SMPListener(commands.Cog):
    role_mapping = {
        888106876854763560: "level-40",
        1121175332205101097: "level-25",
        888106790192033792: "level-15",
        888106415921725471: "level-10",
        888105990598295604: "level-5",
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener(name="on_member_update")
    async def on_role_add(self, before: discord.Member, after: discord.Member):
        if after.roles != before.roles:
            role_added = None

            for role in after.roles:
                if role not in before.roles:
                    role_added = role
                    break

            if not role_added:
                return
        else:
            return

        command = (
            "lp user {username} parent add %s" % SMPListener.role_mapping[role_added.id]
        )

        resp = await self.bot.session.patch(
            f"{self.bot.api_url}/info/permissions?uid={after.id}&permission={command}&key={self.bot.api_key}"
        )
        if resp.status != 200:
            try:
                await after.send(
                    "An error occurred while setting your permissions. Try verifying your account maybe, "
                    f"or contact a staff member.\n\nRole(s) (add): {role_added}"
                )
            except discord.Forbidden:
                pass
            return

    @commands.Cog.listener(name="on_member_update")
    async def on_role_remove(self, before: discord.Member, after: discord.Member):
        if after.roles != before.roles:
            role_removed = None

            for role in before.roles:
                if role not in after.roles:
                    role_removed = role
                    break

            if not role_removed:
                return
        else:
            return

        command = (
            "lpv user {username} parent remove group.%s"
            % SMPListener.role_mapping[role_removed.id]
        )

        resp = await self.bot.session.patch(
            f"{self.bot.api_url}/info/permissions?uid={after.id}&permission={command}&key={self.bot.api_key}"
        )
        if resp.status != 200:
            try:
                await after.send(
                    "An error occurred while setting your permissions. Try verifying your account maybe, "
                    f"or contact a staff member.\n\nRole(s) (remove): {role_removed}"
                )
            except discord.Forbidden:
                pass
            return


async def setup(bot):
    await bot.add_cog(SMPListener(bot))
