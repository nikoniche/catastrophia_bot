import json
import discord
from requests import get
from discord import app_commands, HTTPException
from discord.ext import commands
from secrets import secret
from format_functions import embed_message

GUILD_ID = secret("GUILD_ID")
PING_ACCOUNT_ID = secret("PING_ACCOUNT_ID")
GENERAL_CHANNEL_ID = secret("GENERAL_CHANNEL_ID")
ERROR_CHANNEL_ID = secret("ERROR_CHANNEL_ID")
CATASTROPHIA_API_URL = secret("CATASTROPHIA_API_URL")

REQUEST_ENDPOINT = "/request"

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
                                         f"CatastrophiaBot raised exception: {filtered_exception}"
                                     ))
            return
        else:
            result = response.text

        if result is None:
            print(f"Found no recorded playtime for user {username}")
            return

        try:
            playtime = int(result)
        except ValueError:
            message = "Your playtime is less than 1 hour."
        else:
            formatted_playtime = f"{playtime // 60} hours and {playtime % 60} minutes"
            message = f"{username} has played {formatted_playtime}."
        finally:
            content = embed_message(message)

        try:
            await interaction.response.send_message(content)
        except HTTPException:
            print("Getting rate limited")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        PlaytimeCommands(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
