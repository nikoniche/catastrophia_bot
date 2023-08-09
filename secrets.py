import json
import os

ON_REPLIT = False


def secret(key: str):
    if not ON_REPLIT:
        with open("secrets.json", "r") as r:
            _SECRETS = json.load(r)

        if key not in _SECRETS:
            raise Exception(f"Unknown key: {key}.")

        return _SECRETS[key]
    else:
        return os.getenv(key)
