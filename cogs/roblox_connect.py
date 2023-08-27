import asyncio
import datetime
import math
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
BAN_DURATION = get_config("BAN_DURATION")
UNBAN_CHECK_DELAY = get_config("UNBAN_CHECK_DELAY")

CATASTROPHIA_API_URL = get_secret("CATASTROPHIA_API_URL")
API_KEY_HEADERS = {
    "api-key": get_secret("API_KEY")
}

LINK_ENDPOINT = get_config("LINK_ENDPOINT")
ALL_LINKS_ENDPOINT = get_config("ALL_LINKS_ENDPOINT")


def remove_link_from_server(roblox_username: str) -> None:
    """Sends a post request to the API server to remove a link request from its list.
    Status 2 means a terminated request, either a timeout or a completed request."""

    try:
        requested_url = CATASTROPHIA_API_URL + LINK_ENDPOINT
        requests.post(requested_url, params={
            "roblox_username": roblox_username,
            "status": 2
        }, headers=API_KEY_HEADERS)
    except requests.exceptions.RequestException:
        return


class RobloxConnect(commands.Cog):
    """A command Cog that enables the bot to perform linking operations
    between the discord account and the roblox username."""

    def __init__(self, bot: CatastrophiaBot) -> None:
        self.bot = bot

        # made linking requests to check for by the bot
        self.pending_requests = {}

        self.users_banned_from_linking = []

        # initiating a loop to check for every pending request's status to confirm it or timeout it
        self.check_loop = self.bot.loop.create_task(self.run_check_link_requests())
        self.unban_loop = self.bot.loop.create_task(self.run_check_unbans())

    async def run_check_unbans(self):
        """Checks for users whose linking ban has expired."""

        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await self.check_unbans()
            await asyncio.sleep(UNBAN_CHECK_DELAY)

    async def run_check_link_requests(self):
        """Creates the loop that indefinitely checks for pending requests API server status."""

        # waiting until bot is ready, because bot can not send messages until ready
        await self.bot.wait_until_ready()

        # checking loop
        while not self.bot.is_closed():
            await self.check_link_requests()
            await asyncio.sleep(ATTEMPT_DELAY)

    async def check_unbans(self):
        """Checks all users that are banned from making linking requests if their ban has not expired yet."""

        to_unban = []

        for unban_attempt in self.users_banned_from_linking:
            been_banned_for = unban_attempt["expiration_date"] - time.time()
            if been_banned_for <= 0:
                to_unban.append(unban_attempt)

        for unban in to_unban:
            self.users_banned_from_linking.remove(unban)

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
        for roblox_username in self.pending_requests:
            # gets the client side request for the set roblox username
            local_request: dict = self.pending_requests[roblox_username]
            age = time.time() - local_request["start_time"]
            user: discord.User = local_request["discord_user"]
            channel: discord.Interaction.channel = local_request["request_channel"]

            # checks for requests that exceeded the allowed age and removes them
            if age > CONNECTION_TIMEOUT:
                # informing the discord user who initiated the request
                await channel.send(
                    # f"{user.mention}" + "\n" +
                    embed_message(f"The request to link the username {roblox_username} to {user.display_name} "
                                  f"has expired."))

                # removing it from the client side request list
                to_remove_usernames.append(roblox_username)

        for to_remove_username in to_remove_usernames:
            del self.pending_requests[to_remove_username]

        # checks for every request from the API server and performs the required operations based on their status
        for roblox_username in server_link_requests:
            outdated = False

            # request exceeded allowed time and has already been cancelled on the bot side
            if roblox_username not in self.pending_requests:
                outdated = True

            # links the discord account to the roblox username if the status is 1
            else:
                status = server_link_requests[roblox_username]["status"]

                local_request: dict = self.pending_requests[roblox_username]
                user: discord.User = local_request["discord_user"]
                channel: discord.Interaction.channel = local_request["request_channel"]

                if status == 1 or status == 3:
                    if status == 1:
                        # set the linked role
                        member: discord.Member = channel.guild.get_member(user.id)
                        role = get(member.guild.roles, name="linked")
                        await member.add_roles(role)

                        # set the nickname as the roblox username
                        try:
                            await member.edit(nick=roblox_username)
                        except discord.errors.Forbidden:
                            print("Missing permissions.")

                        # informs the user of the successful linking
                        await channel.send(
                            f"{user.mention}" + "\n" +
                            embed_message(
                                f"Username linking between '{user.name}' and '{roblox_username}' was successful."
                            ))
                    elif status == 3:
                        new_ban = {
                            "discord_user": user,
                            "expiration_date": time.time() + BAN_DURATION
                        }
                        self.users_banned_from_linking.append(new_ban)

                        await channel.send(
                            f"{user.mention}" + "\n" + embed_message(
                                f"Your linking request has been denied, you will not be able to initiate "
                                f"any linking request for {BAN_DURATION // 3600} hours."
                            )
                        )
                    elif status == 4:
                        await channel.send(
                            f"{user.mention}" + "\n" + embed_message(
                                f"This roblox account does not allow username linking."
                            )
                        )

                    # getting rid of the client side request as well
                    del self.pending_requests[roblox_username]
                    outdated = True

            # sending a request to remove the linking request from the API server list
            if outdated:
                remove_link_from_server(roblox_username)

    @app_commands.command(
        name="link",
        description="Initiates the process of linking your discord account to your roblox username."
    )
    async def link(
            self,
            interaction: discord.Interaction,
            roblox_username: str) -> None:
        """A command that begins linking a discord profile to a roblox username."""

        channel: discord.Interaction.channel = interaction.channel
        member: discord.Member = channel.guild.get_member(interaction.user.id)
        linked_role = get(member.guild.roles, name="linked")

        if member.get_role(linked_role.id) is not None:
            await interaction.response.send_message(embed_message(
                f"You are already linked to a roblox username."
            ))
            return

        for local_rblx_name in self.pending_requests:
            local_request: dict = self.pending_requests[local_rblx_name]
            if local_request["discord_user"] == interaction.user:
                await interaction.response.send_message(embed_message(
                    f"You have already issued a linking request. If you misspelled the roblox username, please wait "
                    f"{round(CONNECTION_TIMEOUT - (time.time() - local_request['start_time']))} "
                    f"seconds for the request to expire."
                ))
                return

        for banned_user_dict in self.users_banned_from_linking:
            if banned_user_dict["discord_user"] == interaction.user:
                banned_till_in_seconds = banned_user_dict["expiration_date"] - time.time()
                if banned_till_in_seconds >= 3600:
                    banned_till = f"{math.ceil(banned_till_in_seconds / 3600)} hours"
                else:
                    banned_till = f"{math.ceil(banned_till_in_seconds / 60)} minutes"

                await interaction.response.send_message(embed_message(
                    f"You are banned from making linking requests for another {banned_till}."
                ))
                return

        # initiating the request on the API server
        try:
            requested_url = CATASTROPHIA_API_URL + LINK_ENDPOINT
            response = requests.post(requested_url, params={
                "roblox_username": roblox_username,
                "discord_name": interaction.user.name,
                "status": 0
            }, headers=API_KEY_HEADERS)
        except requests.exceptions.RequestException as e:
            await error_message(self.bot, "Server offline", e)
            return

        # checking for invalid requests
        try:
            response.raise_for_status()
        except Exception as exception:
            await error_message(self.bot, "Roblox link start", exception, response_text=response.text)
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
            f"Sent a request to Catastrophia to link the username {roblox_username} to {interaction.user.display_name}. "
            f"Please confirm your request in a lobby. "
            f"The request will expire after {CONNECTION_TIMEOUT} seconds."
        ))

    @app_commands.command(
        name="removelink",
        description="Unlinks your discord account from the Roblox username."
    )
    async def removelink(
            self,
            interaction: discord.Interaction) -> None:
        """A command that removes the linking between discord account and a roblox username."""

        channel: discord.Interaction.channel = interaction.channel
        member: discord.Member = channel.guild.get_member(interaction.user.id)
        linked_role = get(member.guild.roles, name="linked")

        if member.get_role(linked_role.id) is None:
            await interaction.response.send_message(embed_message(
                f"You are not linked to any username."
            ))
            return
        else:
            await member.remove_roles(linked_role)
            try:
                await member.edit(nick=None)
            except discord.errors.Forbidden:
                pass

            await interaction.response.send_message(embed_message(
                f"Your discord account has been unlinked from the roblox username."
            ))


async def setup(bot: CatastrophiaBot) -> None:
    await bot.add_cog(
        RobloxConnect(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
