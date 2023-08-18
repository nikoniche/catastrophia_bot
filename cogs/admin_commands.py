import discord
from discord import app_commands
from discord.ext import commands
from discord_bot import CatastrophiaBot
from methods import embed_message
from settings import get_secret

GUILD_ID = get_secret("GUILD_ID")


class AdminCommands(commands.Cog):

    def __init__(self, bot: CatastrophiaBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="clear",
        description="Clears all the messages from a set user."
    )
    async def clear_messages(
            self,
            interaction: discord.Interaction,
            user: discord.User,
            channel: discord.TextChannel,
            limit: int = 100) -> None:

        # getting x amount of messages from the user
        user_messages = []
        i = 0
        async for message in channel.history(limit=300):
            # found the desired amount of messages
            if i == limit:
                break

            if message.author == user:
                user_messages.append(message)
                i += 1
        else:
            # found less than the desired images, so changing the amount
            limit = i

        # bot response
        await interaction.response.send_message(
            embed_message(f"Removed {limit} last message(s) from {user.display_name} ({user.name}) in #{channel.name}."),
            ephemeral=True
        )

        # message removal
        await channel.delete_messages(user_messages)


async def setup(bot: CatastrophiaBot) -> None:
    await bot.add_cog(
        AdminCommands(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
