from abstract.agent import Agent
from abstract.nav2d import Navigator2D
from component.action import Action
from component.observation import Observation
from component.sensor.registry import HANDLER_REGISTRY
from component.sensor.request_handler import Handler
from core.logger import log
from map.entity import AgentData, MapEntity
from map.map import Map
from map.position import Position


class Environment:

    _agent_data: dict[Agent, AgentData]

    def __init__(self, problem: str, data: dict):
        self._handlers = {}
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

    def get_tile_data(self, pos: Position) -> MapEntity:
        return self._map.get_position_data(pos)

    def get_tile_as_str(self, pos: Position) -> str:
        if self._map.get_position_data(pos):
            return self._map.get_position_data(pos).name.upper()
        return "EMPTY"

    def validate_action(self, action: Action):
        if action.name == "move":
            agent = action.params.get("agent")
            direction = action.params.get("direction")
            pos = self._agent_data[agent].pos + direction

            log().vprint("agent ", self._agent_data[agent].name, " is at ", self._agent_data[agent].pos, " and is trying to move ", direction," to ", pos)
            tile = self.get_tile_data(pos)
            if tile is None:
                log().vprint("this position is empty")
            elif tile.collideable:
                log().vprint("agent ", self._agent_data[agent].name, " was denied, collideable tile")
                return
            else:
                log().vprint("on this position its a ", tile.name)

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