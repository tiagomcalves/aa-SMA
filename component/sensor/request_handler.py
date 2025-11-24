from abc import ABC, abstractmethod

from component.direction import Direction
from component.observation import Observation, ObservationType
from component.sensor.registry import register_handler, HANDLER_REGISTRY
from map.position import Position


class Handler(ABC):
    @abstractmethod
    def handle(self, request: dict, env) -> dict:
        pass

@register_handler("surroundings")
class SurroundingsHandler(Handler):
    def handle(self, request: dict, env) -> Observation:
        pos = request["position"]
        position = Position(pos[0], pos[1])

        surroundings_payload = {
            "cells": {
                "UP": env.get_data(position + Direction.UP),
                "DOWN": env.get_data(position + Direction.DOWN),
                "LEFT": env.get_data(position + Direction.LEFT),
                "RIGHT": env.get_data(position + Direction.RIGHT)
            }
        }

        print("[Env] processing surroundings:", pos)
        obs = Observation(ObservationType.SURROUNDINGS, surroundings_payload)
        return obs

