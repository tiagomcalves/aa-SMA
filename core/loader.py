import json
from core.logger import log

class ConfigLoader:

    def __init__(self, name: str):
        self._config_data = {}
        with open("problem/" + name + "/config.json", "r", encoding="utf-8") as f:
            self._config_data  = json.load(f)

    def retrieve_data(self, section: str):

        if section == "environment":
            return self._config_data.get("environment")
        elif section == "map":
            return self._config_data.get("environment").get("map")
        elif section == "agents":
            return self._config_data.get("agents")
        return None
