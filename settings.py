import json
import os

ON_REPLIT = True


def get_secret(key: str):
    if not ON_REPLIT:
        with open("secrets.json", "r") as r:
            _SECRETS = json.load(r)

        if key not in _SECRETS:
            raise Exception(f"Unknown key: '{key}'.")

        value = _SECRETS[key]
    else:
        value = os.getenv(key)

    try:
        value = int(value)
    except ValueError:
        pass
    finally:
        return value


def get_config(key: str):
    with open("config.json", "r") as read:
        config = json.load(read)

    if key not in config:
        raise Exception(f"Unknown configuration with the name '{key}'")

    return config[key]
