from discord_bot import CatastrophiaBot
from methods import get_secret
import time

if __name__ == "__main__":
    CatastrophiaBot()

# import requests
#
# url = "https://catastrophiawebserver--nikoniche.repl.co/all_linking_requests"
#
# headers = {
#     "api-key": get_secret("API_KEY")
# }
#
# for i in range(50):
#     response = requests.get(url, headers=headers)
#     print(f"{i}: {response.status_code}")
#     time.sleep(0.1)
