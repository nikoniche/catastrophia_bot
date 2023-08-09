import json
import os

ON_REPLIT = False


def get_secret(key: str):
    if not ON_REPLIT:
        with open("secrets.json", "r") as r:
            _SECRETS = json.load(r)

        if key not in _SECRETS:
            raise Exception(f"Unknown key: '{key}'.")

        return _SECRETS[key]
    else:
        return os.getenv(key)


def get_config(key: str):
    with open("config.json", "r") as read:
        CONFIG = json.load(read)

    if key not in CONFIG:
        raise Exception(f"Unknown configuration with the name '{key}'")

    return CONFIG[key]
