import discord
from discord import app_commands
from discord.ext import commands
from secrets import secret

GUILD_ID = secret("GUILD_ID")


class test(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="test",
        description="Tested command"
    )
    async def testcommand(
            self,
            interaction: discord.Interaction,
            name: str,
            age: int) -> None:
        await interaction.response.send_message(
            f"Tested message response, {name}, {age}"
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        test(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )