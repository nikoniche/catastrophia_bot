import json
import discord
import requests
import time
from requests import get
from discord import app_commands, HTTPException
from discord.ext import commands
from settings import get_secret, get_config
from format_functions import embed_message, format_playtime

GUILD_ID = get_secret("GUILD_ID")
PING_ACCOUNT_ID = get_secret("PING_ACCOUNT_ID")
GENERAL_CHANNEL_ID = get_secret("GENERAL_CHANNEL_ID")
ERROR_CHANNEL_ID = get_secret("ERROR_CHANNEL_ID")
CATASTROPHIA_API_URL = get_secret("CATASTROPHIA_API_URL")

REQUEST_ENDPOINT = "/request"
TOP_TIMES_ENDPOINT = "/top_times"

MIN_TOP_PLAYERS = get_config("MIN_TOP_PLAYERS")
MAX_TOP_PLAYERS = get_config("MAX_TOP_PLAYERS")

CONFIDENTIAL_USERNAMES = get_config("CONFIDENTIAL_USERNAMES")


class PlaytimeCommands(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="playtime",
        description="Shows the user's playtime."
    )
    async def playtime(
            self,
            interaction: discord.Interaction,
            username: str) -> None:

        # blocks sending messages in the general channel
        if interaction.channel_id == GENERAL_CHANNEL_ID:
            print("Attempted to use CatastrophiaBot in general.")
            return

        # ignoring difference between uppercase and lowercase letter / names
        username = username.lower()

        # blocks everyone, but administrators from finding out confidential user's playtime
        if username in CONFIDENTIAL_USERNAMES:
            if not interaction.permissions.administrator:
                print("Regular user tried to get confidential playtime.")
                return

        # retrieves the playtime from the Catastrophia API server
        requested_url = f"{CATASTROPHIA_API_URL}/{REQUEST_ENDPOINT}"
        response = get(
            requested_url,
            params={
                "username": username
            })

        try:
            response.raise_for_status()
        except Exception as exception:
            # catches exceptions when attempting to contact API server
            print(exception)

            # displays the error message in a channel and pings myself
            error_channel = self.bot.get_channel(ERROR_CHANNEL_ID)

            # formatting the exception to avoid leaking the API URL
            filtered_exception = "\n".join([arg.replace(CATASTROPHIA_API_URL, "") for arg in exception.args])
            await error_channel.send("<@" + str(PING_ACCOUNT_ID) + ">" + "\n" +
                                     embed_message(
                                         f"CatastrophiaBot raised an exception while showing a single playtime: {filtered_exception}"
                                     ))
            return
        else:
            playtime = response.json()

        if playtime < 60:
            message = f"{username} has played less than 1 hour."
        else:
            message = f"{username} has played {format_playtime(playtime)}."

        response_message = embed_message(message)

        try:
            await interaction.response.send_message(response_message)
        except HTTPException:
            print("Getting rate limited")

    @app_commands.command(
        name="top_times",
        description="Shows the players with the highest playtimes."
    )
    async def show_top_players(self,
                               interaction: discord.Interaction,
                               amount: int):
        # blocks sending messages in the general channel
        if interaction.channel_id == GENERAL_CHANNEL_ID:
            print("Attempted to use CatastrophiaBot in general.")
            return

        # setting the limit for the amount argument
        if amount < MIN_TOP_PLAYERS or amount > MAX_TOP_PLAYERS:
            await interaction.response.send_message(embed_message(
                f"The limit for the amount is between {MIN_TOP_PLAYERS} and {MAX_TOP_PLAYERS}."
            ))
            return

        requested_url = f"{CATASTROPHIA_API_URL}/{TOP_TIMES_ENDPOINT}"
        response = requests.get(requested_url, params={
            "amount": amount
        })
        print(f"Showing the playtime of the top {amount} players.")

        # avoiding HTTP request exceptions
        try:
            response.raise_for_status()
        except Exception as exception:
            # catches exceptions when attempting to contact API server
            print(exception)

            # displays the error message in a channel and pings myself
            error_channel = self.bot.get_channel(ERROR_CHANNEL_ID)

            # formatting the exception to avoid leaking the API URL
            filtered_exception = "\n".join([arg.replace(CATASTROPHIA_API_URL, "") for arg in exception.args])
            await error_channel.send("<@" + str(PING_ACCOUNT_ID) + ">" + "\n" +
                                     embed_message(
                                         f"CatastrophiaBot raised an exception while showing top times: {filtered_exception}"
                                     ))
            return
        else:
            top_times_dict = response.json()

        # formatting the dictionary with the top times into a string message
        message = ""
        for i, pair in enumerate(top_times_dict.items()):
            position = i + 1

            username, playtime = pair
            message += f"{position}: {username} - {format_playtime(playtime)}\n"

            # dividing message to 10 sections
            if position % 10 == 0 or position == len(top_times_dict):
                # removing last line break
                message = message[:-1]

                # sending a section of the playtimes
                response_channel = interaction.channel
                try:
                    await response_channel.send(embed_message(message))
                except HTTPException:
                    print("Got rate limited.")

                # reset for the next section
                message = ""

                # cooldown to avoid rate limits
                time.sleep(2)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        PlaytimeCommands(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
