from __future__ import annotations
from abc import ABC, abstractmethod
import json

from component.action import Action
from component.observe import Observe
from component.sensor import Sensor

class Agent(ABC):

    _registry = {}
    _sensor : Sensor

    @abstractmethod
    def __init__(self, name: str, properties: dict):
        self.name = name
        self.score = float(0.0)
        self.properties = properties

    @staticmethod
    def load_agents_json(problem: str) -> dict[str, dict]:
        agents = {}
        with open("problem/" + problem + "/agents.json", "r", encoding="utf-8") as f:
            agents = json.load(f)

        return agents

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        Agent._registry[cls.__name__] = cls #automatically register subclass by its class name

    @classmethod
    def create(cls, name: str, data: dict) -> Agent:
        print(f"create( name: \"{name}\", data: {data} ))")
        full_class_str = data["class"]
        module_name, class_name = full_class_str.rsplit(".", 1)
        sub_cls = Agent._registry[class_name]
        return sub_cls(name, data)

    def get_name(self) -> str:
        return self.name

    def observation(self, obs: Observe):
        pass

    def act(self) -> Action:
        pass

    def check_current_state(self, reward: float):
        pass

    def install(self, sensor: Sensor) -> None:
        self._sensor = sensor

    def has_sensor(self) -> bool:
        if self._sensor is None:
            return False
        return True

    def communicate(self, msg: str, sender: Agent):   # thanks to "import annotations", we can have an "Agent" type in its own class
        pass
