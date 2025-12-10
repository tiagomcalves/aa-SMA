import copy
import random
from typing import Optional

from abstract.agent import Agent
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from component.reward import REWARD
from component.sensor.registry import HANDLER_REGISTRY
from core.logger import log
from core.renderer.r_handle import Renderer
from map.entity import AgentData, MapEntity
from map.map import Map
from map.position import Position

class Environment:
    _agent_data: dict[Agent, AgentData]
    renderer: Optional[Renderer] = None

    def __init__(self, problem: str, data: dict, renderer=True):
        self._handlers = {}
        self.problem_type = problem
        if renderer:
            self.renderer = Renderer()

        self._map = Map(problem, data["map"], self)
        self._agent_data = {}

    def register_handler(self, request_type: str):
        handler_cls = HANDLER_REGISTRY.get(request_type)
        if handler_cls is None:
            raise ValueError(f"No sensor handler registered with name '{request_type}'")
        handler_instance = handler_cls()
        self._handlers[request_type] = handler_instance

    def clone(self):
        new_env = Environment.__new__(Environment)

        # There are immutable so they can be referenced still
        new_env.problem_type = self.problem_type
        new_env._handlers = self._handlers
        new_env.renderer = self.renderer

        # deepcopy just the agent data, no need to copy the keys
        # (because they are still referenced by the same agents from Simulator)
        new_env._agent_data = {agent: copy.deepcopy(data) for agent, data in self._agent_data.items()}

        # deepcopy of the Map, fresh map
        new_env._map = Map.__new__(Map)
        new_env._map._env = new_env
        new_env._map._default_empty = copy.deepcopy(self._map._default_empty)
        new_env._map._char_entity_mapping = self._map._char_entity_mapping  # immutable data so no need to deepcopy
        new_env._map._boundaries = copy.deepcopy(self._map._boundaries)
        new_env._map._map_cells = copy.deepcopy(self._map._map_cells)

        new_env._map._max_x = self._map._max_x # just an int
        new_env._map._max_y = self._map._max_y # same
        new_env._map._boundaries = copy.deepcopy(self._map._boundaries) #deepcopy because its a Position

        return new_env

    @staticmethod
    def setup_agent(name: str, data: dict) -> AgentData:
        agent_data = AgentData(data["char"], name, Position(*data["starting_position"]), 0.0)
        agent_data.carrying = None
        return agent_data

    def register_agents(self, agents_dict: dict[Agent, AgentData]) -> None:
        self._agent_data = agents_dict

    def remove_agent(self, agent: Agent):
        log().print(f"Env: remove agent {agent.name}")
        if agent in self._agent_data:
            self._agent_data.pop(agent)

    def send_observation(self, agent: Agent, obs: Observation) -> Observation:
        agent.observation(obs)
        if obs.type == ObservationType.TERMINATE:
            self.remove_agent(agent)
        return obs

    def update(self):
        """ Respawn de Comida (5% chance) """
        if self.problem_type == "foraging":
            if random.random() < 0.05:
                for _ in range(10):
                    x = random.randint(0, self._map.get_max_x() - 1)
                    y = random.randint(0, self._map.get_max_y() - 1)
                    pos = Position(x, y)
                    tile = self.get_tile_data(pos)

                    agent_here = any(adata.pos == pos for adata in self._agent_data.values())

                    if tile.name == "Empty" and not tile.collideable and not agent_here:
                        self._map.add_entity(pos, "FOOD")
                        break

    def act(self, action: Action, agent: Agent):
        if action.name == "move":
            self.validate_move(action)
        elif action.name == "pick":
            self.agent_pick(action)
        elif action.name == "drop":
            self.agent_drop(action)
        else:
            self.send_observation(agent, Observation.denied(action, 0.0))

    def _pack_agents_positions(self) -> dict[Position, str]:
        positions = {}
        for agent, data in self._agent_data.items():
            if not isinstance(agent, Navigator2D): continue
            positions[data.pos] = data.char
        return positions

    def get_map_size(self) -> tuple[int,int]:
        return self._map.get_size()

    def render(self):
        positions = self._pack_agents_positions()
        self._map.render(positions)

    def get_objectives(self):
        objs = {}
        for name in ["Objective", "OBJECTIVE", "Food", "FOOD", "Nest", "NEST"]:
            objs.update(self._map.get_entity_by_name(name))
        return objs

    def get_tile_data(self, pos: Position) -> MapEntity:
        return self._map.get_position_data(pos)

    def get_tile_as_str(self, pos: Position) -> str:
        data = self._map.get_position_data(pos)
        if data: return data.name.upper()
        return "EMPTY"

    def validate_move(self, action: Action):
        agent = action.agent
        direction = action.params.get("direction")

        if direction == Direction.NONE:
            self.send_observation(agent, Observation.denied(action, -2.0))
            return

        current_pos = self._agent_data[agent].pos
        target_pos = current_pos + direction
        tile = self.get_tile_data(target_pos)

        # 1. Verifica Limites e Paredes
        if tile is None:
            self.send_observation(agent, Observation.denied(action, -1.0));
            return
        elif tile.collideable:
            self.send_observation(agent, Observation.denied(action, -0.5));
            return

        # 2. Verifica Colisão com Agentes
        for o_agent, o_data in self._agent_data.items():
            if o_agent is agent: continue
            if o_data.pos == target_pos:
                self.send_observation(agent, Observation.denied(action, -0.2));
                return

        # 3. MOVIMENTO ACEITE
        agent_data = self._agent_data.get(agent)
        agent_data.pos = target_pos

        # --- AUTO-PICKUP (CRÍTICO) ---
        tile_name = tile.name.upper()

        if tile_name in ["FOOD", "RESOURCE", "GARBAGE"] and agent_data.carrying is None:
            agent_data.carrying = 1.0
            self._map.remove_entity(target_pos)  # Remove visualmente AGORA
            log().print(f">>> {agent.name} AUTO-PICKED {tile_name} at {target_pos}")
            self.send_observation(agent, Observation.accepted(action, 50.0))
            return

        # --- AUTO-DROP ---
        if tile_name == "NEST" and agent_data.carrying is not None:
            reward = 100.0 * agent_data.carrying
            agent_data.carrying = None
            log().print(f">>> {action.agent.name} AUTO-DEPOSITED at NEST!")
            self.send_observation(agent, Observation.accepted(action, reward))
            return

        # Movimento normal
        self.send_observation(agent, Observation.accepted(action, -1.0))

    def agent_pick(self, action: Action):
        # Fallback para pick manual
        agent_data = self._agent_data[action.agent]
        tile = self.get_tile_data(agent_data.pos)

        if tile is None:
            self.send_observation(action.agent, Observation.none())
            return

        if tile.name.upper() == "OBJECTIVE":
            self.send_observation(action.agent, Observation.terminate(action, tile.reward))
            return

        if tile.name.upper() in ["FOOD", "RESOURCE", "GARBAGE"]:
            if agent_data.carrying is None:
                agent_data.carrying = 1.0
                self._map.remove_entity(agent_data.pos)
                self.send_observation(action.agent, Observation.accepted(action, 50.0))
            else:
                self.send_observation(action.agent, Observation.denied(action, -0.1))
            return

        self.send_observation(action.agent, Observation.denied(action, -0.1))

    def agent_drop(self, action: Action):
        agent_data = self._agent_data[action.agent]
        tile = self.get_tile_data(agent_data.pos)

        if agent_data.carrying is not None and tile.name.upper() == "NEST":
            reward = 100.0
            agent_data.carrying = None
            self.send_observation(action.agent, Observation.accepted(action, reward))
        else:
            self.send_observation(action.agent, Observation.denied(action, -0.1))

    def serve_data(self, agent: Agent) -> dict[str, Observation]:
        if agent not in self._agent_data: return {}
        sensor_data = {}
        for handler_name, handler_inst in self._handlers.items():
            sensor_data[handler_name] = handler_inst.handle(self._agent_data[agent], self)

        # HACK SENSOR DIREÇÃO
        if self.problem_type == "foraging" and "directions" in sensor_data:
            agent_data = self._agent_data[agent]
            current_pos = agent_data.pos
            target_pos = None

            if agent_data.carrying is not None:
                nests = self._map.get_entity_by_name("Nest")
                if not nests: nests = self._map.get_entity_by_name("NEST")
                if nests:
                    min_dist = float('inf')
                    best_n = None
                    for n_pos in nests.keys():
                        dist = abs(n_pos.x - current_pos.x) + abs(n_pos.y - current_pos.y)
                        if dist < min_dist: min_dist = dist; best_n = n_pos
                    target_pos = best_n
            else:
                foods = self._map.get_entity_by_name("Food")
                if not foods: foods = self._map.get_entity_by_name("FOOD")
                if foods:
                    min_dist = float('inf')
                    best_f = None
                    for f_pos in foods.keys():
                        dist = abs(f_pos.x - current_pos.x) + abs(f_pos.y - current_pos.y)
                        if dist < min_dist: min_dist = dist; best_f = f_pos
                    target_pos = best_f

            if target_pos:
                diff = target_pos - current_pos
                if diff.x == 0 and diff.y == 0:
                    dir_x, dir_y = Direction.NONE, Direction.NONE
                else:
                    dx_val, dy_val = 0, 0
                    if diff.x > 0:
                        dx_val = 1
                    elif diff.x < 0:
                        dx_val = -1
                    if diff.y > 0:
                        dy_val = 1
                    elif diff.y < 0:
                        dy_val = -1

                    dir_x = Direction.RIGHT if dx_val == 1 else (Direction.LEFT if dx_val == -1 else Direction.NONE)
                    dir_y = Direction.DOWN if dy_val == 1 else (Direction.UP if dy_val == -1 else Direction.NONE)

                if hasattr(sensor_data["directions"].payload, 'direction'):
                    sensor_data["directions"].payload.direction = (dir_x, dir_y)

        return sensor_data

    def get_entities_by_type(self, entity_name: str) -> dict:
        return self._map.get_entity_by_name(entity_name)