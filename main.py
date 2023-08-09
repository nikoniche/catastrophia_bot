# from discord_bot import CatastrophiaBot
# CatastrophiaBot()

URL = "https://catastrophiawebserver--nikoniche.repl.co"
# URL = "http://192.168.0.111:9100"

import requests

response = requests.post(f"{URL}/request", params={
    "username": "secret_account_200",
    "playtime": 0,
    "force_change": True
})

response = requests.get(f"{URL}/request", params={
    "username": "secret_account_200"
})

json_response = response.json()
print(json_response)