import asyncio
import discord
import requests
import requests
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import get
from discord_bot import CatastrophiaBot
from settings import get_secret, get_config
from methods import embed_message, format_playtime, error_message

GUILD_ID = get_secret("GUILD_ID")
TOP_PLAYERS_CHANNEL = get_config("TOP_PLAYERS_CHANNEL")

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
TOP_PLAYERS_UPDATE_DELAY = get_config("TOP_PLAYERS_UPDATE_DELAY")

TOP_10_ROLE_ID = get_config("TOP_10_ROLE_ID")
TOP_25_ROLE_ID = get_config("TOP_25_ROLE_ID")
TOP_50_ROLE_ID = get_config("TOP_50_ROLE_ID")
TOP_75_ROLE_ID = get_config("TOP_75_ROLE_ID")
TOP_100_ROLE_ID = get_config("TOP_100_ROLE_ID")


class PlaytimeCommands(commands.Cog):
    """Cog containing commands regarding playtime."""

    def __init__(self, bot: CatastrophiaBot) -> None:
        self.bot = bot

        self.print_top_players.start()

    async def attempt_role_assign(self, roblox_username: str, position: int, top_roles: list):
        discord_id: int = self.bot.link_manager.get_discord_id(roblox_username)
        if discord_id is not None:
            member: discord.Member = self.bot.get_guild(GUILD_ID).get_member(discord_id)
            selected_role = None

            if position <= 10:
                selected_role = 0
            elif position <= 25:
                selected_role = 1
            elif position <= 50:
                selected_role = 2
            elif position <= 75:
                selected_role = 3
            elif position <= 100:
                selected_role = 4

            if selected_role is not None:
                for role in top_roles:
                    member_role = member.get_role(role.id)
                    if member_role is not None:
                        await member.remove_roles(role)
                await member.add_roles(top_roles[selected_role])

    @tasks.loop(hours=1)
    async def print_top_players(self):
        """Sends a list with a desired amount of top ranking players."""

        await self.bot.wait_until_ready()

        if not self.bot.is_ready():
            return

        amount = 100
        channel = self.bot.get_channel(TOP_PLAYERS_CHANNEL)

        await channel.purge(limit=100)

        # setting the limit for the amount argument
        if amount < MIN_TOP_PLAYERS or amount > MAX_TOP_PLAYERS:
            await interaction.response.send_message(embed_message(
                f"The limit for the amount is between {MIN_TOP_PLAYERS} and {MAX_TOP_PLAYERS}."
            ))
            return

        try:
            requested_url = CATASTROPHIA_API_URL + TOP_TIMES_ENDPOINT
            response = requests.get(requested_url, params={"amount": amount}, headers=API_KEY_HEADERS,
                                    timeout=5)
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

        guild = self.bot.get_guild(GUILD_ID)
        top_roles = [
            get(guild.roles, name="Top 10"),
            get(guild.roles, name="Top 25"),
            get(guild.roles, name="Top 50"),
            get(guild.roles, name="Top 75"),
            get(guild.roles, name="Top 100"),
        ]

        # formatting the dictionary with the top times into a string message
        message = ""
        for i, pair in enumerate(top_times_dict.items()):
            position = i + 1

            username, playtime = pair
            message += f"{position}: {username} - {format_playtime(playtime)}\n"

            await self.attempt_role_assign(username, position, top_roles)

            # dividing message to 10 sections
            if position % 25 == 0 or position == len(top_times_dict):
                # removing last line break
                message = message[:-1]

                # sending a section of the playtimes
                await channel.send(embed_message(message))

                # reset for the next section
                message = ""

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
            response = requests.get(requested_url, params={"username": username}, headers=API_KEY_HEADERS,
                           timeout=5)
        except Exception as e:
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
        name="forceplaytime",
        description="Force sets a playtime to a Roblox username."
    )
    async def forceplaytime(self,
                            interaction: discord.Interaction,
                            roblox_username: str,
                            new_playtime: int) -> None:

        # retrieves the playtime from the Catastrophia API server
        requested_url = CATASTROPHIA_API_URL + REQUEST_ENDPOINT
        try:
            response = requests.post(requested_url, params={"username": roblox_username,
                                                            "playtime": new_playtime,
                                                            "force_change": True}, headers=API_KEY_HEADERS,
                                    timeout=5)
        except Exception as e:
            await error_message(self.bot, "Server offline", e)
            return

        # response check
        try:
            response.raise_for_status()
        except Exception as exception:
            await error_message(self.bot, "/forceplaytime", exception, response_text=response.text)
            return

        await interaction.response.send_message(embed_message(
            f"Force set playtime for {roblox_username} to {new_playtime}."
        ), ephemeral=True)


async def setup(bot: CatastrophiaBot) -> None:
    """Cog setup."""

    await bot.add_cog(
        PlaytimeCommands(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
