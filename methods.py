from settings import get_secret

ERROR_CHANNEL_ID = get_secret("ERROR_CHANNEL_ID")
PING_ACCOUNT_ID = get_secret("PING_ACCOUNT_ID")
CATASTROPHIA_API_URL = get_secret("CATASTROPHIA_API_URL")
HIDDEN_URL = CATASTROPHIA_API_URL[CATASTROPHIA_API_URL.find("/") + 2:]


def embed_message(original_message: str) -> str:
    """Wraps a simple string in a simple discord embed format."""
    return f"""```{original_message}```"""


def format_playtime(playtime: int) -> str:
    """Translates playtime in minutes to hours and minutes."""

    formatted_playtime = f"{playtime // 60} hours and {playtime % 60} minutes"
    return formatted_playtime


async def error_message(bot,
                        own_message: str,
                        exception: Exception,
                        response_text=None):
    """Logs a sent error message to a set channel."""

    print(f"Threw: {exception}")

    # displays the error message in a channel and pings myself
    error_channel = bot.get_channel(ERROR_CHANNEL_ID)

    # Replace the CATASTROPHIA_API_URL in the exception message
    filtered_exception = str(exception).replace(CATASTROPHIA_API_URL,
                                                "").replace(HIDDEN_URL, "")

    # log the error
    await error_channel.send(
        "<@" + str(PING_ACCOUNT_ID) + ">" + "\n" +
        embed_message(f"{own_message}: {filtered_exception}\n"
                      f"API response: {response_text}"))
    return
