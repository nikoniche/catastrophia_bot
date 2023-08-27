import settings
from discord_bot import CatastrophiaBot
from keep_alive import start_server

if __name__ == "__main__":
    if settings.ON_REPLIT:
        start_server()

    CatastrophiaBot()
