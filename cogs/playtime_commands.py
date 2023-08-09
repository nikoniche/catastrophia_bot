import json
import discord
import requests
from requests import get
from discord import app_commands, HTTPException
from discord.ext import commands
from secrets import secret
from format_functions import embed_message, format_playtime

GUILD_ID = secret("GUILD_ID")
PING_ACCOUNT_ID = secret("PING_ACCOUNT_ID")
GENERAL_CHANNEL_ID = secret("GENERAL_CHANNEL_ID")
ERROR_CHANNEL_ID = secret("ERROR_CHANNEL_ID")
CATASTROPHIA_API_URL = secret("CATASTROPHIA_API_URL")

REQUEST_ENDPOINT = "/request"
TOP_TIMES_ENDPOINT = "/top_times"

with open("./confidential_usernames.json", "r") as read:
    CONFIDENTIAL_USERNAMES = json.load(read)


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
                "name": username.lower()
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
                                         f"CatastrophiaBot raised exception while showing a single playtime: {filtered_exception}"
                                     ))
            return
        else:
            playtime = response.json()

        if playtime < 60:
            message = "Your playtime is less than 1 hour."
        else:
            formatted_playtime = f"{playtime // 60} hours and {playtime % 60} minutes"
            message = f"{username} has played {formatted_playtime}."

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

        requested_url = f"{CATASTROPHIA_API_URL}/{TOP_TIMES_ENDPOINT}"
        response = requests.get(requested_url)
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
                                         f"CatastrophiaBot raised exception while showing top times: {filtered_exception}"
                                     ))
            return
        else:
            top_times_dict = response.json()

        # formatting the dictionary with the top times into a string message
        message = ""
        for position, pair in enumerate(top_times_dict.items()):
            username, playtime = pair
            message += f"{position+1}. {username}: {format_playtime(playtime)}\n"

        # removing last line break
        message = message[:-1]

        await interaction.response.send_message(embed_message(message))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        PlaytimeCommands(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
