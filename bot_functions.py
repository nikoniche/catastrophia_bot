import time
from discord.ext import commands
from discord.errors import HTTPException
import requests


class BotFunctions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is ready.")

    @commands.command(name="playtime",
                      brief="Shows your playtime",
                      help="-playtime username")
    @commands.guild_only()
    async def show_playtime(self, ctx, name):
        if ctx.channel.id == 657655672082661376:
            return

        result = requests.get(
            "https://playertimewebserver.robinskaba.repl.co/request",
            params={
                "name": name.lower()
            }).text
        print(f"Showing playtime for player {name} with value {result}")

        if result is None:
            print(f"Found no recorded playtime for user {name}")
            return

        try:
            playtime = int(result)
        except ValueError:
            message = "Your playtime is less than 1 hour."
        else:
            playtime = f"{playtime // 60} hours and {playtime % 60} minutes"
            message = f"{name} has played {playtime}."
        finally:
            content = f"""```{message}```"""

        try:
            await ctx.channel.send(content)
        except HTTPException:
            print("Getting rate limited")

    @show_playtime.error
    async def playtime_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            print("misses an argument")

    @commands.command(name="toptimes",
                      brief="Shows top playtimes.",
                      help="-toptimes")
    @commands.guild_only()
    async def show_top_players(self, ctx):
        if ctx.channel.id == 657655672082661376:
            return
        result = requests.get(
            "https://playertimewebserver.robinskaba.repl.co/topten").text
        print(f"Showing top 50 playtimes")

        result = result[:-1]
        players = {
            pair.split("*")[0]: pair.split("*")[1]
            for pair in result.split(";")
        }
        message = ""
        player_number = 1
        for name, playtime in players.items():
            playtime = int(playtime)
            playtime = f"{playtime // 60} hours and {playtime % 60} minutes"
            message += f"{player_number}: {name} - {playtime}\n"

            if player_number % 10 == 0:
                message = message[:-1]
                content = f"""```{message}```"""
                try:
                    await ctx.channel.send(content)
                except HTTPException:
                    print("Getting rate limited")
                message = ""
                time.sleep(1)

            player_number += 1

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id != 935578917635518544:
            return

        if message.author != self.bot.user:
            if message.content[0] != "-":
                await message.delete()

def setup(bot):
    bot.add_cog(BotFunctions(bot))
