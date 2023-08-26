import asyncio
import time
import discord
import requests
from discord import app_commands
from discord.ext import commands
from discord.utils import get
from discord_bot import CatastrophiaBot
from methods import embed_message, error_message
from settings import get_secret, get_config


GUILD_ID = get_secret("GUILD_ID")

CONNECTION_TIMEOUT = get_config("LINK_CHECK_TIMEOUT")
ATTEMPT_DELAY = get_config("LINK_CHECK_ATTEMPT_DELAY")

CATASTROPHIA_API_URL = get_secret("CATASTROPHIA_API_URL")
API_KEY_HEADERS = {
    "api-key": get_secret("API_KEY")
}

LINK_ENDPOINT = get_config("LINK_ENDPOINT")
ALL_LINKS_ENDPOINT = get_config("ALL_LINKS_ENDPOINT")


def remove_link_from_server(roblox_name: str) -> None:
    """Sends a post request to the API server to remove a link request from its list.
    Confirmed status 2 means a terminated request, either a timeout or a completed request."""

    try:
        requested_url = CATASTROPHIA_API_URL + LINK_ENDPOINT
        requests.post(requested_url, params={
            "username": roblox_name,
            "confirmed": 2
        }, headers=API_KEY_HEADERS)
    except requests.exceptions.RequestException:
        print("failed to remove link")
        return


class RobloxConnect(commands.Cog):
    """A command Cog that enables the bot to perform linking operations
    between the discord account and the roblox account."""

    def __init__(self, bot: CatastrophiaBot) -> None:
        self.bot = bot

        # made linking requests to check for by the bot
        self.pending_requests = {}

        # initiating a loop to check for every pending request's status to confirm it or timeout it
        self.check_loop = self.bot.loop.create_task(self.run_check_link_requests())

    async def run_check_link_requests(self):
        """Creates the loop that indefinitely checks for pending requests API server status."""

        # waiting until bot is ready, because bot can not send messages until ready
        await self.bot.wait_until_ready()

        # checking loop
        while not self.bot.is_closed():
            await self.check_link_requests()
            await asyncio.sleep(ATTEMPT_DELAY)

    async def check_link_requests(self):
        """Asks the API server for its recorded requests, compares them to the client side requests
        and performs operations for each request depending on its status and their age."""

        # attempts to get the API server requests
        requested_url = CATASTROPHIA_API_URL + ALL_LINKS_ENDPOINT
        try:
            response = requests.get(requested_url, headers=API_KEY_HEADERS)
        except requests.exceptions.RequestException:
            print(f"Check - Server offline")
            return

        # checks for invalid requests
        try:
            response.raise_for_status()
        except Exception as exception:
            print(f"Check - Incorrect request: {exception}")
            return
        else:
            server_link_requests = response.json()

        to_remove_usernames = []

        # server clean up and confirmations
        for roblox_name in self.pending_requests:
            # gets the client side request for the set roblox account
            local_request: dict = self.pending_requests[roblox_name]
            age = time.time() - local_request["start_time"]

            # checks for requests that exceeded the allowed age and removes them
            if age > CONNECTION_TIMEOUT:
                # informing the discord user who initiated the request
                user: discord.User = local_request["discord_user"]
                channel: discord.Interaction.channel = local_request["request_channel"]
                await channel.send(
                    # f"{user.mention}" + "\n" +
                    embed_message(f"Account linking between "
                                  f"'{user.name}' and '{roblox_name}' has exceeded the allowed time."))

                # removing it from the client side request list
                to_remove_usernames.append(roblox_name)

        for to_remove_username in to_remove_usernames:
            del self.pending_requests[to_remove_username]

        # checks for every request from the API server and performs the required operations based on their status
        for roblox_name in server_link_requests:
            outdated = False

            # request exceeded allowed time and has already been cancelled on the bot side
            if roblox_name not in self.pending_requests:
                print("name no longer in self pending")
                outdated = True

            # links the discord account to the roblox user if the status is 1
            elif server_link_requests[roblox_name] == 1:
                local_request: dict = self.pending_requests[roblox_name]
                user: discord.User = local_request["discord_user"]
                channel: discord.Interaction.channel = local_request["request_channel"]

                # set the linked role
                member: discord.Member = channel.guild.get_member(user.id)
                role = get(member.guild.roles, name="linked")
                await member.add_roles(role)

                # set the nickname as the roblox username
                try:
                    await member.edit(nick=roblox_name)
                except discord.errors.Forbidden:
                    print("Missing permissions.")

                # informs the user of the successful linking
                await channel.send(
                    f"{user.mention}" + "\n" +
                    embed_message(
                        f"Account linking between '{user.name}' and '{roblox_name}' was successful."
                    ))

                # getting rid of the client side request as well
                del self.pending_requests[local_request]
                outdated = True

            # sending a request to remove the linking request from the API server list
            if outdated:
                print("sending request to remove")
                remove_link_from_server(roblox_name)

    @app_commands.command(
        name="link",
        description="Initiates the process of linking your discord account to your roblox account."
    )
    async def connect(
            self,
            interaction: discord.Interaction,
            roblox_username: str) -> None:
        """A command that begins linking a discord profile to a roblox account."""

        # initiating the request on the API server
        try:
            requested_url = CATASTROPHIA_API_URL + LINK_ENDPOINT
            response = requests.post(requested_url, params={
                "username": roblox_username,
                "confirmed": 0
            }, headers=API_KEY_HEADERS)
        except requests.exceptions.RequestException as e:
            await error_message(self.bot, "Server offline", e)
            return

        # checking for invalid requests
        try:
            response.raise_for_status()
        except Exception as exception:
            await error_message(self.bot, "Roblox connect start", exception, response_text=response.text)
            return

        # creating the link request to save for the client side (the discord bot in this case)
        new_link_request = {
            "discord_user": interaction.user,
            "request_channel": interaction.channel,
            "start_time": time.time()
        }
        self.pending_requests[roblox_username] = new_link_request

        # confirmation response
        await interaction.response.send_message(embed_message(
            f"Began account linking for the roblox user '{roblox_username}', please confirm it in Catastrophia."
        ))

    @app_commands.command(
        name="force_link_confirmation",
        description="Force sets the linking for a set roblox username."
    )
    async def force_link_confirmation(
            self,
            interaction: discord.Interaction,
            roblox_username: str,
            confirmation_status: int) -> None:
        """Forcefully requests the API server to set the confirmation status for a set roblox user."""

        # contacting the API server and sending the confirmation status
        try:
            requested_url = CATASTROPHIA_API_URL + LINK_ENDPOINT
            response = requests.post(requested_url, params={
                "username": roblox_username,
                "confirmed": confirmation_status
            }, headers=API_KEY_HEADERS)
        except requests.exceptions.RequestException as e:
            await error_message(self.bot, "Server offline", e)
            return

        # checking for invalid requests
        try:
            response.raise_for_status()
        except Exception as exception:
            await error_message(self.bot, "Roblox connect start", exception, response_text=response.text)
            return

        # confirmation response
        await interaction.response.send_message(embed_message(
            f"Forced linking for '{roblox_username}' to '{confirmation_status}'."
        ))


async def setup(bot: CatastrophiaBot) -> None:
    await bot.add_cog(
        RobloxConnect(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
