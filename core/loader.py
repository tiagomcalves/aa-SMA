import json
from pprint import pprint


class ConfigLoader:

    def __init__(self, name: str):
        self._config_data = {}
        with open("problem/" + name + "/config.json", "r", encoding="utf-8") as f:
            self.config_data  = json.load(f)

        #pprint(config_data)

    def retrieve_data(self, section: str):

        if section == "environment":
            return self.config_data.get("environment")
        elif section == "map":
            return self.config_data.get("environment").get("map")
        elif section == "agents":
            return self.config_data.get("agents")
        return None
