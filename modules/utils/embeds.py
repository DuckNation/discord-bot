import discord


def get_error_embed(description: str) -> discord.Embed:
    return discord.Embed(
        description=description,
        color=discord.Colour.red(),
        timestamp=discord.utils.utcnow(),
    )
