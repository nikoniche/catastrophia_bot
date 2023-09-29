import json
import hashlib

FILE_PATH = "linked_users.json"


class LinkManager:

    def __init__(self):
        self.temp_dict: dict = None
        self.load_file()

    def load_file(self):
        with open(FILE_PATH, "r") as read:
            self.temp_dict = json.load(read)

    def save_file(self):
        with open(FILE_PATH, "w") as write:
            json.dump(self.temp_dict, write, indent=4)

    def add_user(self, roblox_username: str, discord_id: int):
        self.temp_dict[str(discord_id)] = roblox_username
        self.save_file()

    def remove_user(self, discord_id: int):
        del self.temp_dict[str(discord_id)]
        self.save_file()

    def is_discord_id_linked(self, discord_id):
        is_linked = False
        if str(discord_id) in self.temp_dict.keys():
            is_linked = True
        return is_linked

    def get_username(self, discord_id):
        username = self.temp_dict[str(discord_id)]
        self.save_file()
        return username

    def get_discord_id(self, roblox_username):
        roblox_username = roblox_username.lower()
        found_discord_id = None
        for key, value in self.temp_dict.items():
            if value.lower() == roblox_username:
                found_discord_id = int(key)
                break
        return found_discord_id
