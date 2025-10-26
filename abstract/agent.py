from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum

from rdflib import *
from owlready2 import *

import json

class Action:
    pass

class Observation:
    pass

class Sensor:
    pass

class Direction(Enum):
    UP = (0,-1)
    DOWN = (0,1)
    LEFT = (-1,0)
    RIGHT = (1,0)


def load_class(param, param1):
    pass


class Agent(ABC):

    @abstractmethod
    def __init__(self, name: str, properties: dict):
        self.name = name

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

    def concat_header(self, query_body: str) -> str:
        result =f"""
            PREFIX: <{self.onto.base_iri}>
            PREFIX rdf: <{self.RDF}>
            {query_body}
        """
        return result

    def observation(self, obs: Observation):
        pass

    def act(self) -> Action:
        pass

    def check_current_state(self, reward: float):
        pass

    def install(self, sensor: Sensor):
        pass

    def communicate(self, msg: str, sender: Agent):   # thanks to "import annotations"
        pass

    def available_lines(self):
        pass
