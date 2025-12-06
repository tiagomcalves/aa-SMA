from typing import Optional
from abstract.agent import Agent
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from component.sensor.registry import HANDLER_REGISTRY
from component.sensor.request_handler import Handler
from core.logger import log
from map.entity import AgentData, MapEntity
from core.renderer import Renderer
from map.entity import AgentData
from map.map import Map
from map.position import Position


class Environment:

    _agent_data: dict[Agent, AgentData]
    renderer : Optional[Renderer] = None

    def __init__(self, problem: str, data: dict, renderer=True):
        self._handlers = {}
        if renderer:
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

    def remove_agent(self, agent):
        log().print(f"Env: remove agent {agent.name}")
        self._agent_data.pop(agent)

    def send_observation(self, agent: Agent, obs: Observation) -> Observation:
        agent.observation(obs)

        if obs.type == ObservationType.TERMINATE:
            self.remove_agent(agent)

        return obs

    def calculate_reward(self, agent: Agent, action: Action, obs_type: ObservationType):
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

    def get_objectives(self):
        return self._map.get_entity_by_name("OBJECTIVE")

    def get_tile_data(self, pos: Position) -> MapEntity:
        return self._map.get_position_data(pos)

    def get_tile_as_str(self, pos: Position) -> str:
        if self._map.get_position_data(pos):
            return self._map.get_position_data(pos).name.upper()
        return "EMPTY"

    def validate_action(self, action: Action):
        if action.name == "move":
            agent = action.agent
            direction = action.params.get("direction")
            if direction == Direction.NONE:
                log().vprint("agent ", self._agent_data[agent].name, " is choosing to stand still, punished")
                self.send_observation(agent, Observation.denied(action, -1.0))
                return

            pos = self._agent_data[agent].pos + direction

            log().vprint("agent ", self._agent_data[agent].name, " is at ", self._agent_data[agent].pos, " and is trying to move ", direction," to ", pos)
            tile = self.get_tile_data(pos)
            if tile is None:
                log().vprint("this position is empty")
            elif tile.collideable:
                log().vprint("agent ", self._agent_data[agent].name, " was denied, collideable tile")
                self.send_observation(agent, Observation.denied(action, -0.5))
                return
            else:
                log().vprint("on this position its a ", tile.name)

            for o_agent, o_data in self._agent_data.items():
                if o_agent is agent:
                    continue
                if o_data.pos == pos:
                    log().vprint("agent ", self._agent_data[agent].name, " was denied, another agent occupying position")
                    self.send_observation(agent, Observation.denied(action, 0.0))
                    return

            self._agent_data.get(agent).pos = pos
            log().vprint("agent ", self._agent_data[agent].name, " moved")
            self.send_observation(agent, Observation.accepted(action, 1.0))
            return

        if action.name == "pick":
            self.agent_pick(action)
            return

    def agent_pick(self, action):
        # check if agent picked something important
        tile = self.get_tile_data(self._agent_data[action.agent].pos)
        if tile is None:
            self.send_observation(action.agent, Observation.none())
            return

        print(f"env: {action.agent.name} is trying to pick tile {tile.name}")
        if tile.name.upper() == "OBJECTIVE":
            self.send_observation(action.agent, Observation.terminate(action, 100.0))
            return

    def serve_data(self, agent: Agent) -> dict[str, Observation]:
        sensor_data = {}

        for handler in self._handlers:
            sensor_data[handler] = self._handlers[handler].handle(self._agent_data[agent], self)

        return sensor_data