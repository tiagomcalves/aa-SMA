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

        surroundings_payload = {Direction.NONE: env.get_tile_as_str(agent_data.pos),
                                Direction.UP: env.get_tile_as_str(agent_data.pos + Direction.UP),
                                Direction.DOWN: env.get_tile_as_str(agent_data.pos + Direction.DOWN),
                                Direction.LEFT: env.get_tile_as_str(agent_data.pos + Direction.LEFT),
                                Direction.RIGHT: env.get_tile_as_str(agent_data.pos + Direction.RIGHT)}

        log().vprint("[Env] processing surroundings of ",agent_data.name,":", agent_data.pos)

        obs = Observation(ObservationType.SURROUNDINGS,{"cells": surroundings_payload})
        return obs

@registry.register_handler("directions")
class DirectionsHandler(Handler):
    def handle(self, agent_data:AgentData, env) -> Observation:

        objectives = env.get_objectives()

        if objectives is None:
            directions_payload = {Direction.NONE, Direction.NONE}
        else:
            shortest_distance_pos = None
            shortest_distance = None
            (px, py) = agent_data.pos.get()

            for pos, objective in objectives.items():
                (ox,oy) = pos.get()
                dist = (ox-px)**2 + (oy-py)**2

                if shortest_distance is None:
                    shortest_distance = dist
                    shortest_distance_pos = pos
                    continue

                if shortest_distance >= dist:
                    shortest_distance = dist
                    shortest_distance_pos = pos

            (ox,oy) = shortest_distance_pos.get()
            x_direction = Direction.NONE
            y_direction = Direction.NONE

            if ox - px < 0:
                x_direction = Direction.LEFT
            elif ox - px > 0:
                x_direction = Direction.RIGHT

            if oy - py < 0:
                y_direction = Direction.UP
            elif oy - py > 0:
                y_direction = Direction.DOWN

            directions_payload = {x_direction, y_direction}

        log().vprint("[Env] processing directions of ",agent_data.name,":", agent_data.pos)

        obs = Observation(ObservationType.DIRECTION,{"direction": directions_payload})
        return obs

