import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from discord.utils import get

from discord_bot import CatastrophiaBot
from methods import embed_message
from settings import get_secret

GUILD_ID = get_secret("GUILD_ID")


class AdminCommands(commands.Cog):

    def __init__(self, bot: CatastrophiaBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="clear",
        description="Clears all the messages from a set user."
    )
    async def clear_messages(
            self,
            interaction: discord.Interaction,
            user: discord.User,
            channel: discord.TextChannel,
            limit: int = 100) -> None:

        # getting x amount of messages from the user
        user_messages = []
        i = 0
        async for message in channel.history(limit=300):
            # found the desired amount of messages
            if i == limit:
                break

            if message.author == user:
                user_messages.append(message)
                i += 1
        else:
            # found less than the desired images, so changing the amount
            limit = i

        # bot response
        await interaction.response.send_message(
            embed_message(
                f"Removed {limit} last message(s) from {user.display_name} ({user.name}) in #{channel.name}."),
            ephemeral=True
        )

        # message removal
        await channel.delete_messages(user_messages)

    @app_commands.command(
        name="ban",
        description="Permanently bans a user from the discord server."
    )
    @app_commands.choices(delete_messages=[
        Choice(name="None", value=0),
        Choice(name="Last 10 minutes", value=600),
        Choice(name="Last hour", value=3600),
        Choice(name="Last 24 hours", value=86400),
        Choice(name="Last 2 days", value=172800),
        Choice(name="Last 7 days", value=604800)
    ])
    async def ban(self,
                  interaction: discord.Interaction,
                  user: discord.User,
                  delete_messages: Choice[int],
                  reason: str | None = None):

        member: discord.Member = interaction.channel.guild.get_member(user.id)

        await interaction.response.send_message(embed_message(
            f"Banned permanently {user.display_name} (@{user.name}) for {reason}."
        ), ephemeral=True)

        await member.ban(delete_message_seconds=delete_messages.value, reason=reason)

    @app_commands.command(
        name="unban",
        description="Unbans a user from the discord server."
    )
    async def unban(self,
                    interaction: discord.Interaction,
                    username: str):
        """Unbans a user with the set username from the discord server."""

        # retrieves guild
        guild = interaction.channel.guild

        # gets all banned users in the guild
        banned_users = guild.bans(limit=None)
        unban_entry: discord.BanEntry | None = None

        # checks for every banned user if his name doesn't equal the requested username
        async for ban_entry in banned_users:
            if ban_entry.user.name == username:
                unban_entry = ban_entry
                break

        if unban_entry is not None:
            # found the banned user -> unbanning

            await interaction.response.send_message(embed_message(
                f"Unbanned {unban_entry.user.display_name} (@{unban_entry.user.name})"
                f" - previously banned for: {unban_entry.reason}"
            ), ephemeral=True)

            await guild.unban(unban_entry.user)
        else:
            # did not find the banned user

            await interaction.response.send_message(embed_message(
                f"There is no user banned with the name '{username}'."
            ))


    @app_commands.command(
        name="mute",
        description="Permanently mutes a user."
    )
    async def mute(self,
                   interaction: discord.Interaction,
                   user: discord.User):

        guild = interaction.channel.guild
        member: discord.Member = guild.get_member(user.id)
        role = get(guild.roles, name="muted")
        if member.get_role(role.id) is None:
            await interaction.response.send_message(embed_message(
                f"Muted {user.display_name} ({user.name})."
            ))
            await member.add_roles(role)
        else:
            await interaction.response.send_message(embed_message(
                f"The user {user.display_name} ({user.name}) is already muted."
            ))


    @app_commands.command(
        name="unmute",
        description="Unmutes a user."
    )
    async def unmute(self,
                     interaction: discord.Interaction,
                     user: discord.User):

        guild = interaction.channel.guild
        member: discord.Member = guild.get_member(user.id)
        role = get(guild.roles, name="muted")

        if member.get_role(role.id) is not None:
            await interaction.response.send_message(embed_message(
                f"Unmuted {user.display_name} ({user.name})."
            ))
            await member.remove_roles(role)
        else:
            await interaction.response.send_message(embed_message(
                f"The user {user.display_name} ({user.name}) is not muted."
            ))


async def setup(bot: CatastrophiaBot) -> None:
    await bot.add_cog(
        AdminCommands(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
