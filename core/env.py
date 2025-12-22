import copy
import random
from typing import Optional, cast

from abstract.agent import Agent
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from component.reward import REWARD
from component.sensor.registry import HANDLER_REGISTRY
from core.logger import log
from core.renderer.r_handle import Renderer
from map.entity import AgentData, MapEntity, BOUNDARIES_TILE
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

        _lighthouse_ent = self._map.get_entity_by_name("OBJECTIVE")
        _lighthouse_ent = next(iter(_lighthouse_ent))
        self._lighthouse_position : Optional[Position] = self._map.find_ent_pos(_lighthouse_ent)

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
        new_env._map._boundaries_tile = BOUNDARIES_TILE
        new_env._map._char_entity_mapping = self._map._char_entity_mapping  # immutable data so no need to deepcopy
        new_env._map._boundaries = copy.deepcopy(self._map._boundaries)
        new_env._map._map_cells = copy.deepcopy(self._map._map_cells)

        new_env._map._max_x = self._map._max_x # just an int
        new_env._map._max_y = self._map._max_y # same
        new_env._map._boundaries = copy.deepcopy(self._map._boundaries) #deepcopy because its a Position
        new_env._map.position_visits = copy.deepcopy(self._map.position_visits)
        new_env._lighthouse_position = self._lighthouse_position

        return new_env

    @staticmethod
    def setup_agent(name: str, data: dict) -> AgentData:
        agent_data = AgentData(data["char"], name, Position(*data["starting_position"]), 0.0)
        return agent_data

    def register_agents(self, agents_dict: dict[Agent, AgentData]) -> None:
        self._agent_data = agents_dict
        for agent, data in self._agent_data.items():
            print("registering agent", agent, "position")
            self._map.add_count_to_position(data.pos)

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

                    if not tile and not agent_here:
                        self._map.add_entity(pos, "FOOD")
                        break

    def act(self, action: Action, agent: Agent):
        if action.name == "move":
            self.validate_move(action)
        # elif action.name == "pick":
        #     self.agent_pick(action)
        # elif action.name == "drop":
        #     self.agent_drop(action)
        else:
            self.send_observation(agent, Observation.denied(action, 0.0))

    def _pack_agents_positions(self) -> dict[Position, str]:
        positions = {}
        for agent, data in self._agent_data.items():
            if not isinstance(agent, Navigator2D): continue
            positions[data.pos] = data.char
        return positions

    def get_map_size(self) -> tuple[int,int]:
        return self._map.get_max_x(), self._map.get_max_y()

    def render(self):
        positions = self._pack_agents_positions()
        self._map.render(positions)

    def get_objectives(self):
        objs = {}
        for name in ["OBJECTIVE", "FOOD", "NEST"]:
            objs.update(self._map.get_entity_by_name(name))
        return objs

    def get_tile_data(self, pos: Position) -> MapEntity:
        return self._map.get_position_data(pos)

    def get_tile_as_str(self, pos: Position) -> str:
        data = self._map.get_position_data(pos)
        if data: return data.name.upper()
        return "EMPTY"

    def move_agent(self, agent, pos):
        agent_data = self._agent_data.get(agent)
        agent_data.pos = pos
        self._map.add_count_to_position(pos)

    def validate_move(self, action: Action):
        agent = action.agent
        direction = action.params.get("direction")

        # if direction == Direction.NONE:
        #     self.send_observation(agent, Observation.denied(action, REWARD.STAND_STILL))
        #     return

        current_pos = self._agent_data[agent].pos
        target_pos = current_pos + direction
        tile = self.get_tile_data(target_pos)

        # 1. Verifica Limites e Paredes
        if tile and tile is BOUNDARIES_TILE:
            # self.send_observation(agent, Observation.denied(action, REWARD.OUT_OF_BOUNDS))
            self.send_observation(agent, Observation.response(REWARD.OUT_OF_BOUNDS))
            return
        elif tile and tile.collideable:
            # self.send_observation(agent, Observation.denied(action, REWARD.BUMP_COLLIDEABLE))
            self.send_observation(agent, Observation.response(REWARD.BUMP_COLLIDEABLE))
            return

        # 2. Verifica Colisão com Agentes
        for o_agent, o_data in self._agent_data.items():
            if o_agent is agent: continue
            if o_data.pos == target_pos:
                # self.send_observation(agent, Observation.denied(action, REWARD.BUMP_AGENT))
                self.send_observation(agent, Observation.response(REWARD.BUMP_AGENT))
                return

        # 3. MOVIMENTO ACEITE
        self.move_agent(agent, target_pos)

        if tile is None:
            if self.problem_type == "lighthouse":
            #     calculate reward based on direction
                new_distance_evaluation = self._get_distance_to_objective(current_pos, target_pos)

                if new_distance_evaluation == -1 or new_distance_evaluation == 0:
                    self.send_observation(agent, Observation.response(REWARD.MOVED, True))
                    return
                
                if new_distance_evaluation == 1:
                    self.send_observation(agent, Observation.response(REWARD.MOVED_CLOSER, True))
                    return

            self.send_observation(agent, Observation.response(REWARD.MOVED, True))
            return

        # --- AUTO-PICKUP  ---
        tile_name = tile.name.upper()

        agent_data = self._agent_data.get(agent)
        if tile_name in ["FOOD", "RESOURCE", "GARBAGE"]:
            if agent_data.carrying is not None:
                self.send_observation(agent, Observation.response(REWARD.MOVED, True))
                return

            agent_data.carrying = 1.0

            navigator = cast(Navigator2D, agent)
            navigator.base_attributes.carrying = True
            navigator.ep.total_food_collected += 1

            self._map.remove_entity(target_pos)  # Remove visualmente AGORA
            log().print(f">>> {agent.name} AUTO-PICKED {tile_name} at {target_pos}")
            #self.send_observation(agent, Observation.accepted(action, 50.0))
            self.send_observation(agent, Observation.response(50.0, True))
            return


        # --- AUTO-DROP ---
        if tile_name == "NEST":
            if agent_data.carrying is None:
                self.send_observation(agent, Observation.response(REWARD.MOVED, True))
                return

            reward = 200.0 * agent_data.carrying
            agent_data.carrying = None

            navigator = cast(Navigator2D, agent)
            navigator.ep.total_food_delivered += 1
            navigator.ep.successful_returns += 1

            log().print(f">>> {action.agent.name} AUTO-DEPOSITED at NEST!")
            #self.send_observation(agent, Observation.accepted(action, reward))
            self.send_observation(agent, Observation.response(reward, True))
            return

        # --- Reach Lighhouse ---
        if tile_name == "OBJECTIVE":
            log().print(f">>> {action.agent.name} REACHED LIGHTHOUSE!")
            self.send_observation(agent, Observation.terminate(action, tile.reward))
            return

    def _get_distance_to_objective(self, current_pos, target_pos):
        old_pos_dist = self._calculate_distance_to_objective(current_pos)
        new_pos_dist = self._calculate_distance_to_objective(target_pos)

        if old_pos_dist < new_pos_dist:
            return -1
        elif old_pos_dist > new_pos_dist:
            return 1
        return 0

    def _calculate_distance_to_objective(self, position):
        goal_x = self._lighthouse_position.x
        goal_y = self._lighthouse_position.y
        return abs(position.x - goal_x) + abs(position.y - goal_y)

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
                nests = self._map.get_entity_by_name("NEST")
                if nests:
                    min_dist = float('inf')
                    best_n = None
                    for n_pos in nests.keys():
                        dist = abs(n_pos.x - current_pos.x) + abs(n_pos.y - current_pos.y)
                        if dist < min_dist: min_dist = dist; best_n = n_pos
                    target_pos = best_n
            else:
                foods = self._map.get_entity_by_name("FOOD")
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

    def retrieve_visited_positions(self):
        visited_pos = {}
        for pos, count in self._map.position_visits.items():
            visited_pos[(pos.x,pos.y)] = count
        return visited_pos