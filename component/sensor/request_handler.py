from abc import ABC, abstractmethod

from component.sensor import registry
from core.logger import log
from component.direction import Direction
from component.observation import Observation, ObservationType
from map.entity import AgentData
from map.position import Position


class Handler(ABC):
    @abstractmethod
    def handle(self, agent_data:AgentData, env) -> dict:
        pass

@registry.register_handler("surroundings")
class SurroundingsHandler(Handler):
    def handle(self, agent_data:AgentData, env) -> Observation:

        surroundings_payload = {Direction.NONE: env.get_data(agent_data.pos),
                                Direction.UP: env.get_data(agent_data.pos + Direction.UP),
                                Direction.DOWN: env.get_data(agent_data.pos + Direction.DOWN),
                                Direction.LEFT: env.get_data(agent_data.pos + Direction.LEFT),
                                Direction.RIGHT: env.get_data(agent_data.pos + Direction.RIGHT)}

        log().vprint("[Env] processing surroundings of ",agent_data.name,":", agent_data.pos)

        obs = Observation(ObservationType.SURROUNDINGS,{"cells": surroundings_payload})
        return obs

