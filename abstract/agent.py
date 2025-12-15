from __future__ import annotations
from abc import ABC, abstractmethod
from enum import auto, Enum
from typing import Optional

from abstract.utils.action_builder import ActionBuilder
from abstract.utils.state import State
from core.logger import log
from component.action import Action
from component.observation import Observation, ObservationType
from component.sensor.sensor import Sensor

class AgentStatus(Enum):
    INITIALIZING = auto()
    RUNNING = auto()
    IDLE = auto()
    TERMINATED = auto()

class Agent(ABC):

    _registry = {}
    _env : Environment

    @abstractmethod
    def __init__(self, problem: str, name: str, properties: dict):
        self.name = name
        self.timestamp = properties["timestamp"]
        self.score = float(0.0)
        self.properties = properties
        self.status = AgentStatus.INITIALIZING
        self._sensor : Optional[Sensor] = None
        self.curr_observations: dict[ObservationType, Observation] = {}
        self.curr_action : Optional[Action] = None
        #self.state = State(problem, name)
        self.action = ActionBuilder(self)

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        Agent._registry[cls.__name__] = cls #automatically register subclass by its class name

    @classmethod
    def create(cls, problem: str, name: str, data: dict) -> Agent:
        log().vprint(f"create( name: \"{name}\", data: {data} ))")
        full_class_str = data["class"]
        module_name, class_name = full_class_str.rsplit(".", 1)
        sub_cls = Agent._registry[class_name]
        return sub_cls(problem, name, data)

    def get_name(self) -> str:
        return self.name

    @abstractmethod
    def observation(self, obs: Observation):
        pass

    def has_observations(self) -> bool:
        if not self.curr_observations:
            return False
        return True

    @abstractmethod
    def act(self) -> Action:
        pass

    def check_current_state(self, reward: float):
        pass

    def set_env(self, env: Environment) -> None:
        self._env = env

    def get_env(self) -> Environment:
        return self._env

    def install(self, sensor: Sensor) -> None:
        self._sensor = sensor

    def has_sensor(self) -> bool:
        if self._sensor is None:
            return False
        return True

    @abstractmethod
    def use_sensor(self) -> Observation:
        pass

    def communicate(self, msg: str, sender: Agent):   # thanks to "import annotations", we can have an "Agent" type in its own class
        pass

    @abstractmethod
    def start_episode(self) -> None:
        pass