import json


with open("config.json") as file:
    data = json.load(file)
    BOT_TOKEN = data.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Something from the following list was not given: BOT_TOKEN")
