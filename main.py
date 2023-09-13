import settings
from discord_bot import CatastrophiaBot
from keep_alive import start_server

if __name__ == "__main__":
    # don't start keep_alive server on local run
    if settings.ON_REPLIT:
        start_server()

    # discord bot start
    CatastrophiaBot()
