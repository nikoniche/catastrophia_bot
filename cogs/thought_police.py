import json
import discord
from discord import app_commands
from discord.ext import commands
from discord import Embed
from discord_bot import CatastrophiaBot
from methods import embed_message
from settings import get_secret
from discord.app_commands import Choice


GUILD_ID = get_secret("GUILD_ID")


def create_crime_report(user_id: int,
                        channel_id: int,
                        crime_type: str,
                        offensive_message_content: str,
                        punishment: str) -> Embed:
    """Creates a discord Embed that will display the information about the message that was moderated."""

    # initiating the embed
    embed = discord.Embed(title="Thought crime detected", description="A user is suspected of a thoughtcrime.",
                          color=0xff0000)

    # big brother thumbnail
    embed.set_thumbnail(
        url="https://caquiscaidosblog.files.wordpress.com/2009/01/1984-movie-bb2_a.jpg")

    # embed fields
    embed.add_field(name="User", value=f"<@{user_id}>", inline=True)
    embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=True)
    embed.add_field(name="Crime", value=crime_type, inline=True)
    embed.add_field(name="Message", value=offensive_message_content, inline=False)
    embed.add_field(name="Punishment", value=punishment, inline=False)

    # footer for design purposes
    embed.set_footer(text="CatastrophiaBot")

    return embed


class ThoughtPolice(commands.Cog):

    CRIME_TYPE_CHOICES = [
        Choice(name="Racism", value="racism"),
        Choice(name="Game promotion", value="game_promotion"),
        Choice(name="Mild vulgarism", value="mild_vulgarism"),
        Choice(name="Strong vulgarism", value="strong_vulgarism")
    ]

    PUNISHMENT_CHOICES = [
        Choice(name="Ban", value="ban"),
        Choice(name="Mute", value="mute"),
        Choice(name="Warn", value="warn")
    ]

    class OffensiveManager:

        OFFENSIVE_LIST_PATH = "offensive_list.json"

        def __init__(self):

            # main internal raw list
            with open(self.OFFENSIVE_LIST_PATH, "r") as read:
                self.raw_list = json.load(read)

            # loading the two main separate lists
            self.full_exact_match_list = None
            self.full_any_match_list = None
            self.reload_full_lists()

        def reload_full_lists(self):
            """Loads all sections and their lists to two separate lists to make checking for offensive words easier."""

            self.full_exact_match_list = []
            self.full_any_match_list = []
            for crime_type, specs in self.raw_list.items():
                self.full_exact_match_list += specs["exact_match_list"]
                self.full_any_match_list += specs["any_match_list"]

        def save_raw_list_to_file(self):
            """Saves the internal raw list to a json file."""

            with open(self.OFFENSIVE_LIST_PATH, "w") as w:
                json.dump(self.raw_list, w, indent=4)

        def get_crime_details(self, offensive_word: str) -> tuple | None:
            """Extracts information about a set word."""

            # browses every section and checks if the word is any of the section lists
            for crime_type, specs in self.raw_list.items():

                # checking if the word is in either of the lists and setting the list_type at the same time
                list_type = None
                if offensive_word in specs["exact_match_list"]:
                    list_type = "exact_match_list"
                elif offensive_word in specs["any_match_list"]:
                    list_type = "any_match_list"

                # found the word in either of the lists
                if list_type is not None:
                    return crime_type, specs["punishment"], list_type

            # no record of the word was found
            return None

        def add_word(self, word: str, crime_type: str, list_type: str) -> None:
            """Adds a word to the internal raw list of offensive words."""

            # appends to the correct section, should not raise an exception, because all, but the word argument should
            # be pre-made choices
            self.raw_list[crime_type][list_type].append(word)
            self.save_raw_list_to_file()
            self.reload_full_lists()

        def remove_word(self, word: str) -> bool:
            """Removes a word from the internal raw list of offensive words."""

            # gets information about the word
            details = self.get_crime_details(word)

            # checks if the word is recorded
            if details is None:
                return False

            # proceeds to remove the word from the corresponding section
            crime_type, _, list_type = details
            self.raw_list[crime_type][list_type].remove(word)
            self.save_raw_list_to_file()
            self.reload_full_lists()

            # removed successfully
            return True

        def change_punishment(self, crime_type: str, new_punishment: str) -> None:
            """Changes the punishment for a set crime type."""

            # should not throw an error as crime_type is a pre-made choice
            self.raw_list[crime_type]["punishment"] = new_punishment
            self.save_raw_list_to_file()
            self.reload_full_lists()

    def __init__(self, bot: CatastrophiaBot) -> None:
        self.bot = bot
        self.offensive_manager = ThoughtPolice.OffensiveManager()

    async def moderate_message(self, message: discord.Message):
        verdict = None

        # find an offence that matches any part of the message
        for any_match_word in self.offensive_manager.full_any_match_list:
            if any_match_word in message.content:
                crime_type, punishment, _ = self.offensive_manager.get_crime_details(any_match_word)
                verdict = crime_type, punishment, any_match_word
                break
        else:
            # find full exact match offences
            message_words = message.content.split(" ")
            for message_word in message_words:
                if message_word in self.offensive_manager.full_exact_match_list:
                    crime_type, punishment, _ = self.offensive_manager.get_crime_details(message_word)
                    verdict = crime_type, punishment, message_word
                    break

        if verdict is not None:
            crime_type, punishment, offensive_word = verdict
            # remove the offensive message
            await message.delete()

            # send a report
            report_embed = create_crime_report(
                message.author.id,
                message.channel.id,
                crime_type,
                message.content.replace(
                    offensive_word,
                    f"**{offensive_word}**"
                ),
                punishment
            )

            removed_message_embed = Embed(title=f"Removed a message from {message.author.display_name}", color=0xffffff,
                                          description=f"**Reason:** oldspeak")
            removed_message_embed.set_footer(text=f"CatastrophiaBot")
            await message.channel.send(embed=removed_message_embed)
            await message.channel.send(embed=report_embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Moderates user sent messages."""

        # preventing a loop where bot controls its own message
        if message.author.id == self.bot.user.id:
            return

        if message.channel.id != 778258665525346345:
            # dev block only work in testing
            return

        await self.moderate_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _, message: discord.Message):
        """Moderates message edits."""

        # testing channel only
        if message.channel.id != 778258665525346345:
            return

        # blocking message cycle
        if message.author.id == self.bot.user.id:
            return

        await self.moderate_message(message)

    @app_commands.command(
        name="add_offensive_word",
        description="Adds a word to the list of offensive words."
    )
    @app_commands.choices(
        offence_type=CRIME_TYPE_CHOICES,
        match_type=[
            Choice(name="Exact match", value="exact_match_list"),
            Choice(name="Any match", value="any_match_list")
        ]
    )
    @app_commands.describe(
        offensive_word="The word that will be added to the list. Should be a single word.",
        offence_type="What type of offence the word is.",
        match_type="Exact match will trigger only isolated words.\n"
                   "Any match will trigger if found anywhere in the message."
    )
    async def add_offensive_word(self,
                                 interaction: discord.Interaction,
                                 offensive_word: str,
                                 offence_type: Choice[str],
                                 match_type: Choice[str]):
        """Adds a new offensive word to the list of the set type and the set offence section."""

        # adds the word to the offensive manager internal list, should not raise an error as all, but the word
        # are pre-made choices
        self.offensive_manager.add_word(
            offensive_word,
            offence_type.value,
            match_type.value
        )

        await interaction.response.send_message(embed_message(
            f"Added '{offensive_word}', type: {offence_type.name} - {match_type.name}"
        ))

    @app_commands.command(
        name="remove_offensive_word",
        description="Removes an offensive word from the list."
    )
    @app_commands.describe(
        word_to_remove="Word that will be removed from the list of offensive words."
    )
    async def remove_offensive_word(self,
                                    interaction: discord.Interaction,
                                    word_to_remove: str):
        """Removes a set word from the list of offensive words."""

        # attempts to remove a message from the internal offensive managers list
        if self.offensive_manager.remove_word(word_to_remove):
            await interaction.response.send_message(embed_message(
                f"Successfully removed the word '{word_to_remove}' from the list."
            ))
        else:
            # informs about the failure of the command (did not find the word)
            await interaction.response.send_message(embed_message(
                f"Failed to find the word '{word_to_remove}' in the list."
            ))

    @app_commands.command(
        name="change_punishment",
        description="Changes the punishment for a set crime type."
    )
    @app_commands.choices(
        crime_type=CRIME_TYPE_CHOICES,
        punishment=PUNISHMENT_CHOICES
    )
    @app_commands.describe(
        crime_type="The crime type to set the punishment for.",
        punishment="New punishment to set for the crime type."
    )
    async def change_punishment(self,
                                interaction: discord.Interaction,
                                crime_type: Choice[str],
                                punishment: Choice[str]):
        """A command that changes the punishment for a set crime type."""

        self.offensive_manager.change_punishment(
            crime_type.value,
            punishment.value
        )

        await interaction.response.send_message(embed_message(
            f"Changed the punishment for {crime_type.name} to '{punishment.name}'."
        ))


async def setup(bot: CatastrophiaBot) -> None:
    await bot.add_cog(
        ThoughtPolice(bot),
        guilds=[discord.Object(id=GUILD_ID)]
    )
