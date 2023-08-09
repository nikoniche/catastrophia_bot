def embed_message(original_message: str) -> str:
    return f"""```{original_message}```"""


def format_playtime(playtime: int) -> str:
    formatted_playtime = f"{playtime // 60} hours and {playtime % 60} minutes"
    return formatted_playtime
