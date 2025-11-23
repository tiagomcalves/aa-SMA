from typing import Union

from abstract.agent import Agent
from component.action import Action
from component.observe import Observe
from component.sensor.registry import HANDLER_REGISTRY
from component.sensor.request_handler import Handler
from map.entity import MapEntity
from map.map import Map
from map.position import Position


class Environment:

    def __init__(self, problem: str, data: dict):
        self._handlers = {}
        self._map = Map(problem, data["map"], self)

    def register_handler(self, request_type: str):
        handler_cls = HANDLER_REGISTRY.get(request_type)
        if handler_cls is None:
            raise ValueError(f"No sensor handler registered with name '{request_type}'")
        handler_instance = handler_cls()
        self._handlers[request_type] = handler_instance

    def send_observation(self, agent: Agent) -> Observe:
        pass

    def update(self):
        pass

    def act(self, action: Action, agent: Agent):
        pass

    def render(self, agent_positions: dict[Position, str]):
        self._map.render(agent_positions)

    def get_data(self, pos: Position) -> str:
        return self._map.get_position_data(pos)

    def handle_request(self, request: dict) -> dict:
        req_type = request.get("type")
        handler = self._handlers.get(req_type)
        if handler:
            return handler.handle(request, self)
        else:
            raise ValueError(f"No handler registered for request type '{req_type}'")
