import discord
import requests
from requests import get
from discord import app_commands
from discord.ext import commands
from discord_bot import CatastrophiaBot
from settings import get_secret, get_config
from methods import embed_message, format_playtime, error_message

GUILD_ID = get_secret("GUILD_ID")

# constants for requests
CATASTROPHIA_API_URL = get_secret("CATASTROPHIA_API_URL")
API_KEY_HEADERS = {
    "api-key": get_secret("API_KEY")
}
REQUEST_ENDPOINT = get_config("REQUEST_ENDPOINT")
TOP_TIMES_ENDPOINT = get_config("TOP_TIMES_ENDPOINT")

# command constants
MIN_TOP_PLAYERS = get_config("MIN_TOP_PLAYERS")
MAX_TOP_PLAYERS = get_config("MAX_TOP_PLAYERS")
CONFIDENTIAL_USERNAMES = get_config("CONFIDENTIAL_USERNAMES")


class PlaytimeCommands(commands.Cog):
    """Cog containing commands regarding playtime."""

    def __init__(self, bot: CatastrophiaBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="playtime",
        description="Shows the user's playtime."
    )
    async def playtime(
            self,
            interaction: discord.Interaction,
            username: str) -> None:
        """Shows a playtime for a set player."""

        # ignoring difference between uppercase and lowercase letter / names
        username = username.lower()

        # blocks everyone, but administrators from finding out confidential user's playtime
        if username in CONFIDENTIAL_USERNAMES:
            if not interaction.permissions.administrator:
                print("Regular user tried to get confidential playtime.")
                return

        # retrieves the playtime from the Catastrophia API server
        requested_url = CATASTROPHIA_API_URL + REQUEST_ENDPOINT
        try:
            response = get(requested_url, params={"username": username}, headers=API_KEY_HEADERS)
        except requests.exceptions.RequestException as e:
            await error_message(self.bot, "Server offline", e)
            return

        # response check
        try:
            response.raise_for_status()
        except Exception as exception:
            await error_message(self.bot, "/playtime", exception, response_text=response.text)
            return
        else:
            playtime = response.json()

        # formatting playtime and skipping playtimes, that are less than 1 hour
        if playtime < 60:
            message = f"{username} has played less than 1 hour."
        else:
            message = f"{username} has played {format_playtime(playtime)}."

        # responding with the result
        response_message = embed_message(message)
        await interaction.response.send_message(response_message)

    @app_commands.command(
        name="toptimes",
        description="Shows the players with the highest playtimes."
    )
    async def show_top_players(self,
                               interaction: discord.Interaction,
                               amount: int):
        """Sends a list with a desired amount of top ranking players."""

        # setting the limit for the amount argument
        if amount < MIN_TOP_PLAYERS or amount > MAX_TOP_PLAYERS:
            await interaction.response.send_message(embed_message(
                f"The limit for the amount is between {MIN_TOP_PLAYERS} and {MAX_TOP_PLAYERS}."
            ))
            return

        try:
            requested_url = CATASTROPHIA_API_URL + TOP_TIMES_ENDPOINT
            response = requests.get(requested_url, params={"amount": amount}, headers=API_KEY_HEADERS)
        except requests.exceptions.RequestException as e:
            await error_message(self.bot, "Server offline", e)
            return

        # avoiding HTTP request exceptions
        try:
            response.raise_for_status()
        except Exception as exception:
            await error_message(self.bot, "/toptimes", exception, response_text=response.text)
            return
        else:
            top_times_dict = response.json()
            top_times_dict = dict(sorted(top_times_dict.items(), key=lambda item: item[1], reverse=True))

        # formatting the dictionary with the top times into a string message
        message = ""
        for i, pair in enumerate(top_times_dict.items()):
            position = i + 1

            username, playtime = pair
            message += f"{position}: {username} - {format_playtime(playtime)}\n"

            # dividing message to 10 sections
            if position % 25 == 0 or position == len(top_times_dict):
                # removing last line break
                message = message[:-1]

                # sending a section of the playtimes
                response_channel = interaction.channel
                await response_channel.send(embed_message(message))

                # reset for the next section
                message = ""


async def setup(bot: CatastrophiaBot) -> None:
    """Cog setup."""

    await bot.add_cog(
        PlaytimeCommands(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
