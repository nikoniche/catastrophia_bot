import os

import discord
from discord.ext import commands
from secrets import secret

BOT_TOKEN = secret("BOT_TOKEN")
APPLICATION_ID = secret("APPLICATION_ID")
GUILD_ID = secret("GUILD_ID")


class CatastrophiaBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="-",
            intents=discord.Intents.all(),
            application_id=APPLICATION_ID
        )
        self.run(BOT_TOKEN)

    async def setup_hook(self):
        for path in os.listdir("cogs"):
            if ".py" not in path:
                continue

            cog_name = path.replace(".py", "")
            cog_path = f"cogs.{cog_name}"
            await self.load_extension(cog_path)

        await self.tree.sync(guild=discord.Object(id=GUILD_ID))

    async def on_ready(self):
        print(f"{self.user} bot is ready.")