from typing import Optional
from abstract.agent import Agent
from abstract.nav2d import Navigator2D
from component.action import Action
from component.observation import Observation
from component.sensor.registry import HANDLER_REGISTRY
from component.sensor.request_handler import Handler
from core.logger import log
from core.renderer import Renderer
from map.entity import AgentData
from map.map import Map
from map.position import Position


class Environment:

    _agent_data: dict[Agent, AgentData]
    renderer : Optional[Renderer] = None

    def __init__(self, problem: str, data: dict, renderer=True):
        self._handlers = {}
        if renderer == True:
            self.renderer = Renderer()
            
        self._map = Map(problem, data["map"], self)

    def register_handler(self, request_type: str):
        handler_cls = HANDLER_REGISTRY.get(request_type)
        if handler_cls is None:
            raise ValueError(f"No sensor handler registered with name '{request_type}'")
        handler_instance = handler_cls()
        self._handlers[request_type] = handler_instance

    @staticmethod
    def setup_agent(name: str, data: dict) -> AgentData:
        return AgentData(data["char"], name, Position(*data["starting_position"]), 0.0)

    def register_agents(self, agents_dict: dict[Agent, AgentData]) -> None:
        self._agent_data = agents_dict

    def send_observation(self, agent: Agent) -> Observation:
        pass

    def update(self):
        pass

    def act(self, action: Action, agent: Agent):
        pass

    def _pack_agents_positions(self) -> dict[Position, str]:
        positions = {}

        for agent, data in self._agent_data.items():
            if not isinstance(agent, Navigator2D):
                continue

            positions[data.pos] = data.char

        return positions

    def render(self):
        self._map.render(self._pack_agents_positions())

    def get_agent_state(self):
        pass

    def get_data(self, pos: Position) -> str:
        return self._map.get_position_data(pos)

    def validate_action(self, action: Action):
        if action.name == "move":
            agent = action.params.get("agent")
            direction = action.params.get("direction")
            pos = self._agent_data[agent].pos + direction

            log().vprint("agent ", self._agent_data[agent].name, " is at ", self._agent_data[agent].pos, " and is trying to move ", direction," to ", pos)
            tile = self.get_data(pos)
            log().vprint("on this position its a ", tile)
                         
            if tile in ("BOUNDARIE", "WALL"):
                log().vprint("agent ", self._agent_data[agent].name, " was denied, collideable tile")
                return

            for o_agent, o_data in self._agent_data.items():
                if o_agent is agent:
                    continue
                if o_data.pos == pos:
                    log().vprint("agent ", self._agent_data[agent].name, " was denied, another agent occupying position")
                    return


            self._agent_data.get(agent).pos = pos
            log().vprint("agent ", self._agent_data[agent].name, " moved")


    def serve_data(self, agent: Agent) -> dict[str, Observation]:
        sensor_data = {}

        for handler in self._handlers:
            sensor_data[handler] = self._handlers[handler].handle(self._agent_data[agent], self)

        return sensor_data