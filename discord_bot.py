import os
import discord
from discord.ext import commands
from settings import get_secret

BOT_TOKEN = get_secret("BOT_TOKEN")
APPLICATION_ID = get_secret("APPLICATION_ID")
GUILD_ID = get_secret("GUILD_ID")


class CatastrophiaBot(commands.Bot):
    """Main bot class for CatastrophiaBot"""

    def __init__(self):
        # bot settings
        super().__init__(
            command_prefix="-",
            intents=discord.Intents.all(),
            application_id=APPLICATION_ID
        )

        # bot start
        self.run(BOT_TOKEN)

    async def setup_hook(self):
        """Performs setup operations necessary before bot start."""

        # formatting and loading all cogs
        for path in os.listdir("cogs"):
            if ".py" not in path:
                continue

            cog_name = path.replace(".py", "")
            cog_path = f"cogs.{cog_name}"
            await self.load_extension(cog_path)

        await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Setup hook finished.")

    async def on_ready(self):
        """Bot is ready."""

        print(f"{self.user} bot is ready.")
