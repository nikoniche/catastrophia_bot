import asyncio
import json
import os
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

    class OffensiveManager:
        def __init__(self):
            self.raw_list = None
            self.full_exact_match_list = None
            self.full_any_match_list = None

            self.reload()

        def reload(self):
            with open("offensive_list.json", "r") as read:
                self.raw_list = json.load(read)

            self.full_exact_match_list = []
            self.full_any_match_list = []
            for crime_type, specs in self.raw_list.items():
                self.full_exact_match_list += specs["exact_match_list"]
                self.full_any_match_list += specs["any_match_list"]

            print(f"Finished reloading OffensiveManager.\n"
                  f"{self.full_exact_match_list=}\n"
                  f"{self.full_any_match_list=}")

        def get_crime_details(self, offensive_word: str) -> dict:
            for crime_type, specs in self.raw_list.items():
                if offensive_word in specs["exact_match_list"] + specs["any_match_list"]:
                    return {
                        crime_type, specs["punishment"]
                    }

            raise Exception(f"ThoughtPolice has no records for the word '{offensive_word}'.")

    def __init__(self, bot: CatastrophiaBot) -> None:
        self.bot = bot
        self.offensive_manager = ThoughtPolice.OffensiveManager()

    async def moderate_message(self, message: discord.Message):
        verdict = None

        # find an offence that matches any part of the message
        for any_match_word in self.offensive_manager.full_any_match_list:
            if any_match_word in message.content:
                crime_type, punishment = self.offensive_manager.get_crime_details(any_match_word)
                verdict = crime_type, punishment, any_match_word
                break
        else:
            # find full exact match offences
            message_words = message.content.split(" ")
            for message_word in message_words:
                if message_word in self.offensive_manager.full_exact_match_list:
                    crime_type, punishment = self.offensive_manager.get_crime_details(message_word)
                    verdict = crime_type, punishment, message_word
                    break

        if verdict is not None:
            crime_type, punishment, offensive_word = verdict
            # remove the offensive message
            await message.delete()

            # send a report
            report_embed = create_crime_report(
                message.author.id,
                message.channel.id,
                crime_type,
                message.content.replace(
                    offensive_word,
                    f"**{offensive_word}**"
                ),
                punishment
            )

            removed_message_embed = Embed(title=f"Removed a message from {message.author.display_name}", color=0xffffff,
                                          description=f"**Reason:** oldspeak")
            removed_message_embed.set_footer(text=f"CatastrophiaBot")
            await message.channel.send(embed=removed_message_embed)
            await message.channel.send(embed=report_embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # preventing a loop where bot controls its own message
        if message.author.id == self.bot.user.id:
            return

        if message.channel.id != 778258665525346345:
            # dev block only work in testing
            return

        await self.moderate_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _, message: discord.Message):
        # testing channel only
        if message.channel.id != 778258665525346345:
            return

        # blocking message cycle
        if message.author.id == self.bot.user.id:
            return

        await self.moderate_message(message)


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
