from __future__ import annotations
from abc import ABC, abstractmethod
import importlib
import json

from component.action import Action
from component.observation import Observation
from component.sensor import Sensor

class Agent(ABC):

    @abstractmethod
    def __init__(self, name: str, properties: dict):
        self.name = name
        self.properties = properties

    @staticmethod
    def create(agent_name: str, file: str) -> Agent:

        agents = {}
        with open(file, "r", encoding="utf-8") as f:
            agents = json.load(f)

        # hardcoded agent classes in "agent/" directory
        full_class_str = "agent." + agents[agent_name]["class"]
        #print("full class: ", full_class_str)

        module_name, class_name = full_class_str.rsplit(".", 1)
        module = importlib.import_module(module_name)

        agent_subclass = getattr(module, class_name)

        return agent_subclass(agent_name, agents[agent_name])

    def get_name(self) -> str:
        return self.name

    def observation(self, obs: Observation):
        pass

    def act(self) -> Action:
        pass

    def check_current_state(self, reward: float):
        pass

    def install(self, sensor: Sensor):
        pass

    def communicate(self, msg: str, sender: Agent):   # thanks to "import annotations", we can have an "Agent" type in its own class
        pass

