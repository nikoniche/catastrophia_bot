import json
import os

ON_REPLIT = True


def get_secret(key: str) -> str | int:
    """Returns an environmental variable based on the current platform."""

    if not ON_REPLIT:
        # local way of retrieving env variables

        with open("secrets.json", "r") as r:
            _SECRETS = json.load(r)

        if key not in _SECRETS:
            raise Exception(f"Unknown key: '{key}'.")

        value = _SECRETS[key]
    else:
        # repl-it way
        value = os.getenv(key)

    # attempting to convert to an int if possible, because repl-it does not support int secrets
    try:
        value = int(value)
    except ValueError:
        pass
    finally:
        return value


def get_config(key: str) -> str | int:
    """Loads a config value from a json file, they don't have to be private."""

    with open("config.json", "r") as read:
        config = json.load(read)

    if key not in config:
        raise Exception(f"Unknown configuration with the name '{key}'")

    return config[key]
