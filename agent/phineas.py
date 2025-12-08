import random
import pickle
import os
from typing import Optional

from abstract.agent import AgentStatus
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from map.position import Position


class Phineas(Navigator2D):
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)

        self._position = Position(*properties.get("starting_position", (0, 0)))
        self.char = properties.get("char", "P")
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.1
        self.mode = properties.get("mode", "LEARNING")

        self.carrying = False
        self.q_table = {}
        self.visit_counts = {}

        self.known_nest_position: Optional[Position] = None

        self.pos_history = []
        self.panic_mode = 0

        self.last_state = None
        self.last_action = None
        self.last_attempted_action = None
        self.last_extrinsic_reward = 0.0

        self.load_knowledge()

    def use_sensor(self) -> Observation:
        obs = self._sensor.get_info(self)
        self.state.update_sensor_data(True, obs)

        if obs.surroundings:
            self.curr_observations[ObservationType.SURROUNDINGS] = obs.surroundings
            self._scan_for_nest(obs.surroundings.payload.cells)

        if obs.directions:
            self.curr_observations[ObservationType.DIRECTION] = obs.directions

        if obs.location:
            self.curr_observations[ObservationType.LOCATION] = obs.location
            tile = getattr(obs.location.payload, 'tile_name', "").upper()
            if tile == "NEST":
                self.known_nest_position = self._position

        return obs

    def _scan_for_nest(self, cells: dict):
        for direction, content in cells.items():
            if content.upper() in ["NEST", "N"]:
                self.known_nest_position = self._position + direction

    def observation(self, obs: Observation):
        if obs.type == ObservationType.ACCEPTED:
            self.last_extrinsic_reward = obs.payload.reward

            if self.last_attempted_action:
                if self.last_attempted_action.name == "move":
                    direction = self.last_attempted_action.params.get("direction")
                    if direction:
                        self._position = self._position + direction

                    if obs.payload.reward >= 40.0:
                        self.carrying = not self.carrying

                elif self.last_attempted_action.name == "pick":
                    self.carrying = True
                elif self.last_attempted_action.name == "drop":
                    self.carrying = False

            self.pos_history.append(self._position)
            if len(self.pos_history) > 10: self.pos_history.pop(0)

        elif obs.type == ObservationType.TERMINATE:
            self.status = AgentStatus.TERMINATED
            self.save_knowledge()

    def _get_state_key(self) -> str:
        return f"C:{1 if self.carrying else 0}|Pos:{self._position}"

    def _learn(self, current_state: str):
        if not self.last_state or not self.last_action: return
        old_q = self.q_table.get((self.last_state, self.last_action), 0.0)

        bonus = 1.0 / (self.visit_counts.get(current_state, 0) + 1)
        total_r = self.last_extrinsic_reward + bonus

        max_next = max([self.q_table.get((current_state, str(m)), 0.0)
                        for m in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]])

        new_q = old_q + self.learning_rate * (total_r + (self.discount_factor * max_next) - old_q)
        self.q_table[(self.last_state, self.last_action)] = new_q

    def _navigate_euclidean(self, target: Position, free_moves: list) -> Direction:
        best_move = None
        min_dist_sq = float('inf')

        # Só itera sobre movimentos LIVRES
        for move in free_moves:
            next_pos = self._position + move
            diff = target - next_pos
            dist_sq = (diff.x ** 2) + (diff.y ** 2)

            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                best_move = move
            elif dist_sq == min_dist_sq and random.random() < 0.5:
                best_move = move

        return best_move if best_move else random.choice(free_moves)

    def act(self) -> Action:
        if not self.has_observations(): self.use_sensor()

        # 1. INSTINTO
        obs_loc = self.curr_observations.get(ObservationType.LOCATION)
        if obs_loc:
            tile = getattr(obs_loc.payload, 'tile_name', "").upper()
            if not self.carrying and tile in ["FOOD", "RESOURCE"]:
                act = self.action.pick();
                self.last_attempted_action = act;
                return act
            if self.carrying and tile == "NEST":
                act = self.action.drop();
                self.last_attempted_action = act;
                return act

        # 2. BARREIRA DE PAREDES (CRÍTICO)
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        walls = ["WALL", "OBSTACLE", "#", "X"]

        free_moves = []
        if obs_surr:
            # Filtra todas as direções que têm parede
            for d, c in obs_surr.payload.cells.items():
                if d != Direction.NONE and c.upper() not in walls:
                    free_moves.append(d)
        else:
            free_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        if not free_moves:
            act = self.action.wait();
            self.last_attempted_action = act;
            return act

        final_dir = None

        # 3. PÂNICO
        if self.panic_mode > 0:
            self.panic_mode -= 1
            final_dir = random.choice(free_moves)
        elif len(set(self.pos_history[-6:])) <= 2 and len(self.pos_history) >= 6:
            self.panic_mode = 5
            final_dir = random.choice(free_moves)

        # 4. MODO RETORNO
        elif self.carrying:
            target = self.known_nest_position
            if not target:
                if ObservationType.DIRECTION in self.curr_observations:
                    obs_dir = self.curr_observations[ObservationType.DIRECTION]
                    dx, dy = obs_dir.payload.direction
                    target = Position(self._position.x + (15 * dx), self._position.y + (15 * dy))
                else:
                    target = Position(1, 1)

            final_dir = self._navigate_euclidean(target, free_moves)

        # 5. MODO EXPLORAÇÃO
        else:
            state = self._get_state_key()
            self.visit_counts[state] = self.visit_counts.get(state, 0) + 1
            if self.mode == "LEARNING": self._learn(state)

            if self.mode == "TEST" or random.random() > self.epsilon:
                max_q = float('-inf')
                best_opts = []
                # Só verifica Q-values das direções LIVRES
                for m in free_moves:
                    q = self.q_table.get((state, str(m)), 0.0)
                    if q > max_q:
                        max_q = q; best_opts = [m]
                    elif q == max_q:
                        best_opts.append(m)
                final_dir = random.choice(best_opts) if best_opts else random.choice(free_moves)
            else:
                final_dir = random.choice(free_moves)

        # BLINDAGEM FINAL: Se por milagre escolher uma direção proibida
        if final_dir not in free_moves:
            final_dir = random.choice(free_moves)

        self.last_state = state if not self.carrying else None
        self.last_action = str(final_dir)
        act = self.action.move(final_dir)
        self.last_attempted_action = act
        return act

    def save_knowledge(self):
        try:
            with open(f"qtable_{self.name}.pkl", "wb") as f:
                pickle.dump(self.q_table, f)
        except:
            pass

    def load_knowledge(self):
        if os.path.exists(f"qtable_{self.name}.pkl"):
            try:
                with open(f"qtable_{self.name}.pkl", "rb") as f:
                    self.q_table = pickle.load(f)
            except:
                pass