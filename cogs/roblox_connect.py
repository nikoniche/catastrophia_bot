import asyncio
import math
import time
import discord
import requests
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import get
from discord_bot import CatastrophiaBot
from methods import embed_message, error_message
from discord.errors import HTTPException
from settings import get_secret, get_config
import functools
import typing

GUILD_ID = get_secret("GUILD_ID")

# time configurations
CONNECTION_TIMEOUT = get_config("LINK_CHECK_TIMEOUT")
ATTEMPT_DELAY = get_config("LINK_CHECK_ATTEMPT_DELAY")
BAN_DURATION = get_config("BAN_DURATION")
UNBAN_CHECK_DELAY = get_config("UNBAN_CHECK_DELAY")

# request constants
CATASTROPHIA_API_URL = get_secret("CATASTROPHIA_API_URL")
API_KEY_HEADERS = {"api-key": get_secret("API_KEY")}
LINK_ENDPOINT = get_config("LINK_ENDPOINT")
ALL_LINKS_ENDPOINT = get_config("ALL_LINKS_ENDPOINT")

# command config
CONFIDENTIAL_USERNAMES = get_config("CONFIDENTIAL_USERNAMES")


def remove_link_from_server(roblox_username: str) -> None:
    """Sends a post request to the API server to remove a link request from its list.
    Status 2 means a terminated request, either a timeout or a completed request."""

    try:
        requested_url = CATASTROPHIA_API_URL + LINK_ENDPOINT
        requests.post(requested_url,
                      params={
                          "roblox_username": roblox_username,
                          "status": 2
                      },
                      headers=API_KEY_HEADERS)
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

        self.check_unbans.start()
        self.check_link_requests.start()

    @tasks.loop(hours=12)
    async def check_unbans(self):
        """Checks all users that are banned from making linking requests if their ban has not expired yet."""

        if not self.bot.is_ready():
            return

        to_unban = []

        for unban_attempt in self.users_banned_from_linking:
            been_banned_for = unban_attempt["expiration_date"] - time.time()
            if been_banned_for <= 0:
                to_unban.append(unban_attempt)

        for unban in to_unban:
            self.users_banned_from_linking.remove(unban)

    @tasks.loop(seconds=10)
    async def check_link_requests(self):
        """Asks the API server for its recorded requests, compares them to the client side requests
        and performs operations for each request depending on its status and their age."""

        if not self.bot.is_ready():
            return

        # attempts to get the API server requests
        requested_url = CATASTROPHIA_API_URL + ALL_LINKS_ENDPOINT
        try:
            response = requests.get(requested_url, headers=API_KEY_HEADERS, timeout=5)
        except Exception as e:
            # await error_message(self.bot, "ALL LINK GET REQUEST", e)
            return

        # checks for invalid requests
        try:
            response.raise_for_status()
        except Exception as exception:
            print(f"Check - Incorrect request")
            # await error_message(self.bot, "ALL LINK response.raise_for_status()", exception, response.content)
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
            channel: discord.Interaction.channel = local_request[
                "request_channel"]

            # checks for requests that exceeded the allowed age and removes them
            if age > CONNECTION_TIMEOUT:
                # informing the discord user who initiated the request
                await channel.send(
                    # f"{user.mention}" + "\n" +
                    embed_message(
                        f"The request to link the username {roblox_username} to {user.display_name} "
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
                channel: discord.Interaction.channel = local_request[
                    "request_channel"]

                if status == 1 or status == 3 or status == 4:
                    if status == 1:
                        # set the linked role
                        member: discord.Member = channel.guild.get_member(
                            user.id)
                        role = get(member.guild.roles, name="linked")
                        await member.add_roles(role)

                        # set the nickname as the roblox username
                        try:
                            await member.edit(nick=roblox_username)
                        except discord.errors.Forbidden:
                            print("Missing permissions.")

                        # informs the user of the successful linking
                        await channel.send(
                            f"{user.mention}" + "\n" + embed_message(
                                f"Username linking between '{user.name}' and '{roblox_username}' was successful."
                            ))
                    elif status == 3:
                        # request was denied, bans the user from making other requests to prevent spam
                        new_ban = {
                            "discord_user": user,
                            "expiration_date": time.time() + BAN_DURATION
                        }
                        self.users_banned_from_linking.append(new_ban)

                        # informing the user
                        await channel.send(
                            f"{user.mention}" + "\n" + embed_message(
                                f"Your linking request has been denied, you will not be able to initiate "
                                f"any linking request for {BAN_DURATION // 3600} hours."
                            ))
                    elif status == 4:
                        # the roblox account is below 13 years of age, doesn't allow showing discord
                        await channel.send(
                            f"{user.mention}" + "\n" + embed_message(
                                f"This roblox account does not allow username linking."
                            ))

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
    async def link(self, interaction: discord.Interaction,
                   roblox_username: str) -> None:
        """A command that begins linking a discord profile to a roblox username."""

        # fetching the member class and the linked role
        channel: discord.Interaction.channel = interaction.channel
        member: discord.Member = channel.guild.get_member(interaction.user.id)
        linked_role = get(member.guild.roles, name="linked")

        # disallows linking when already linked
        if member.get_role(linked_role.id) is not None:
            await interaction.response.send_message(
                embed_message(f"You are already linked to a roblox username."))
            return

        # checks if there is an active request from the user
        for local_roblox_username in self.pending_requests:
            local_request: dict = self.pending_requests[local_roblox_username]
            if local_request["discord_user"] == interaction.user:
                await interaction.response.send_message(
                    embed_message(
                        f"You have already issued a linking request. "
                        f"If you misspelled the roblox username, please wait "
                        f"{round(CONNECTION_TIMEOUT - (time.time() - local_request['start_time']))} "
                        f"seconds for the request to expire."))
                return

        # checks if the user isn't banned from linking requests
        for banned_user_dict in self.users_banned_from_linking:
            if banned_user_dict["discord_user"] == interaction.user:
                # counting remaining banned time
                banned_till_in_seconds = banned_user_dict[
                    "expiration_date"] - time.time()
                if banned_till_in_seconds >= 3600:
                    banned_till = f"{math.ceil(banned_till_in_seconds / 3600)} hours"
                else:
                    banned_till = f"{math.ceil(banned_till_in_seconds / 60)} minutes"

                # response
                await interaction.response.send_message(
                    embed_message(
                        f"You are banned from making linking requests for another {banned_till}."
                    ))
                return

        # disallows users to link to admin accounts
        if roblox_username.lower() in CONFIDENTIAL_USERNAMES:
            await interaction.response.send_message(
                embed_message(
                    f"You can not make a link request to this username."))
            return

        # initiating the request on the API server
        try:
            requested_url = CATASTROPHIA_API_URL + LINK_ENDPOINT
            response = requests.post(requested_url,
                                     params={
                                         "roblox_username": roblox_username,
                                         "discord_name": interaction.user.name,
                                         "status": 0
                                     },
                                     headers=API_KEY_HEADERS)
        except requests.exceptions.RequestException as e:
            await error_message(self.bot, "Server offline", e)
            return

        # checking for invalid requests
        try:
            response.raise_for_status()
        except Exception as exception:
            await error_message(self.bot,
                                "Roblox link start",
                                exception,
                                response_text=response.text)
            return

        # creating the link request to save for the client side (the discord bot in this case)
        new_link_request = {
            "discord_user": interaction.user,
            "request_channel": interaction.channel,
            "start_time": time.time()
        }
        self.pending_requests[roblox_username] = new_link_request

        # confirmation response
        await interaction.response.send_message(
            embed_message(
                f"Sent a request to Catastrophia to link "
                f"the username {roblox_username} to {interaction.user.display_name}. "
                f"Please confirm your request in a lobby. "
                f"The request will expire after {CONNECTION_TIMEOUT} seconds.")
        )

    @app_commands.command(
        name="removelink",
        description="Unlinks your discord account from the Roblox username.")
    async def removelink(self,
                         interaction: discord.Interaction) -> None:
        """A command that removes the linking between discord account and a roblox username."""

        # fetching the member class and the linked role
        channel: discord.Interaction.channel = interaction.channel
        member: discord.Member = channel.guild.get_member(interaction.user.id)
        linked_role = get(member.guild.roles, name="linked")

        if member.get_role(linked_role.id) is None:
            # user isn't linked, but only linked roles have access to the command anyway
            await interaction.response.send_message(
                embed_message(f"You are not linked to any username."))
            return
        else:
            # removes the link role
            await member.remove_roles(linked_role)

            # too many request cooldown
            time.sleep(1)

            try:
                await member.edit(nick=None)
                # too many request cooldown
                time.sleep(1)
            except discord.errors.Forbidden:
                print("Forbidden from removing nickname.")

            try:
                # unlink response, for some reason throws a rate limited error
                await interaction.response.send_message(
                    embed_message(
                        f"Your discord account has been unlinked from the roblox username."
                    ))
            except HTTPException:
                print("RemoveLink - TOO MANY REQUESTS")


async def setup(bot: CatastrophiaBot) -> None:
    """Cog setup."""

    await bot.add_cog(RobloxConnect(bot), guilds=[discord.Object(id=GUILD_ID)])
