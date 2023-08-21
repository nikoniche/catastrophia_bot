import asyncio
import json
import time
import discord
import requests
from discord import app_commands
from discord.ext import commands
from discord.utils import get
from discord import Embed
from discord_bot import CatastrophiaBot
from methods import embed_message, error_message
from settings import get_secret, get_config


GUILD_ID = get_secret("GUILD_ID")


def create_crime_report(user_id: int,
                        channel_id: int,
                        crime_type: str,
                        offensive_message_content: str,
                        punishment: str) -> Embed:
    embed = discord.Embed(title="Thought crime detected", description="A user is suspected of a thoughtcrime.",
                          color=0xff0000)
    embed.set_thumbnail(
        url="https://caquiscaidosblog.files.wordpress.com/2009/01/1984-movie-bb2_a.jpg")
    embed.add_field(name="User", value=f"<@{user_id}>", inline=True)
    embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=True)
    embed.add_field(name="Crime", value=crime_type, inline=True)
    embed.add_field(name="Message", value=offensive_message_content, inline=False)
    embed.add_field(name="Punishment", value=punishment, inline=False)
    embed.set_footer(text="CatastrophiaBot")
    return embed


class ThoughtPolice(commands.Cog):
    def __init__(self, bot: CatastrophiaBot) -> None:
        self.bot = bot

        self.offense_list: dict | None = None
        self.reload_offense_list()

    def reload_offense_list(self):
        with open("../offensive_list.json", "r") as read:
            self.offense_list = json.load(read)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        for category, specs in self.offense_list.items():
            specs: dict

            pass


    @app_commands.command(
        name="embed_test"
    )
    async def embed_test(self,
                         interaction: discord.Interaction):

        report_embed = create_crime_report(
            1057447283064569967,
            657655672082661376,
            "treason",
            "DOWN WITH **BIG BROTHER.**",
            "Execution (ban)"
        )
        await interaction.response.send_message(embed=report_embed)


async def setup(bot: CatastrophiaBot) -> None:
    await bot.add_cog(
        ThoughtPolice(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
