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

LINK_ENDPOINT = get_config("LINK_ENDPOINT")
ALL_LINKS_ENDPOINT = get_config("ALL_LINKS_ENDPOINT")


def remove_link_from_server(roblox_name: str) -> bool:
    """Sends a post request to the API server to remove a link request from its list.
    Confirmed status 2 means a terminated request, either a timeout or a completed request."""

    try:
        requested_url = CATASTROPHIA_API_URL + LINK_ENDPOINT
        response = requests.post(requested_url, params={
            "username": roblox_name,
            "confirmed": 2
        })
    except requests.exceptions.RequestException:
        # server is offline
        return False
    else:
        # check for incorrect request
        try:
            response.raise_for_status()
        except Exception:
            return False
        else:
            return True


class RobloxConnect(commands.Cog):
    def __init__(self, bot: CatastrophiaBot) -> None:
        self.bot = bot

        self.pending_requests = {}

        self.check_loop = self.bot.loop.create_task(self.run_check_link_requests())

    async def run_check_link_requests(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await self.check_link_requests()
            await asyncio.sleep(ATTEMPT_DELAY)

    async def check_link_requests(self):
        requested_url = CATASTROPHIA_API_URL + ALL_LINKS_ENDPOINT

        try:
            response = requests.get(requested_url)
        except requests.exceptions.RequestException:
            print(f"Check - Server offline")
            return

        try:
            response.raise_for_status()
        except Exception as exception:
            print(f"Check - Incorrect request: {exception}")
            return
        else:
            server_link_requests = response.json()
            # print(f"Current server requests: {server_link_requests}")

        # server clean up and confirmations
        for rblx_name in self.pending_requests:
            local_request: dict = self.pending_requests[rblx_name]
            age = time.time() - local_request["start_time"]
            if age > CONNECTION_TIMEOUT:
                user: discord.User = local_request["discord_user"]
                channel: discord.Interaction.channel = local_request["request_channel"]
                await channel.send(
                    # f"{user.mention}" + "\n" +
                    embed_message(
                    f"Account linking between '{user.name}' and '{rblx_name}' has exceeded the allowed time."
                ))
                del self.pending_requests[rblx_name]

        for rblx_name in server_link_requests:
            outdated = False

            if server_link_requests[rblx_name] == 1:
                # request was confirmed

                user: discord.User = local_request["discord_user"]
                channel: discord.Interaction.channel = local_request["request_channel"]

                # set the linked role
                member: discord.Member = channel.guild.get_member(user.id)
                role = get(member.guild.roles, name="linked")
                await member.add_roles(role)

                # set the nickname as the roblox username
                try:
                    await member.edit(nick=rblx_name)
                except discord.errors.Forbidden:
                    print("Missing permissions.")

                local_request = self.pending_requests[rblx_name]

                await channel.send(
                    f"{user.mention}" + "\n" +
                    embed_message(
                        f"Account linking between '{user.name}' and '{rblx_name}' was successful."
                    ))

                del self.pending_requests[local_request]

                outdated = True
            elif rblx_name not in self.pending_requests:
                # request exceeded allowed time and has already been cancelled on the bot side
                outdated = True

            if outdated:
                success = remove_link_from_server(rblx_name)
                if not success:
                    print("Failed to remove link.")

    @app_commands.command(
        name="link",
        description="Initiates the process of linking your discord account to your roblox account."
    )
    async def connect(
            self,
            interaction: discord.Interaction,
            roblox_username: str) -> None:

        # connect stuff
        try:
            requested_url = CATASTROPHIA_API_URL + LINK_ENDPOINT
            response = requests.post(requested_url, params={
                "username": roblox_username,
                "confirmed": 0
            })
        except requests.exceptions.RequestException as e:
            await error_message(self.bot, "Server offline", e)
            return

        try:
            response.raise_for_status()
        except Exception as exception:
            await error_message(self.bot, "Roblox connect start", exception, response_text=response.text)
            return
        else:
            print("API received linking request.")

        new_link_request = {
            "discord_user": interaction.user,
            "request_channel": interaction.channel,
            "start_time": time.time()
        }

        self.pending_requests[roblox_username] = new_link_request

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

        print("Connect command initiated.")
        # connect stuff
        try:
            requested_url = CATASTROPHIA_API_URL + LINK_ENDPOINT
            response = requests.post(requested_url, params={
                "username": roblox_username,
                "confirmed": confirmation_status
            })
        except requests.exceptions.RequestException as e:
            await error_message(self.bot, "Server offline", e)
            return

        try:
            response.raise_for_status()
        except Exception as exception:
            await error_message(self.bot, "Roblox connect start", exception, response_text=response.text)
            return
        else:
            print("API received linking request.")

        await interaction.response.send_message(embed_message(
            f"Forced linking for '{roblox_username}' to '{confirmation_status}'."
        ))


async def setup(bot: CatastrophiaBot) -> None:
    await bot.add_cog(
        RobloxConnect(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
