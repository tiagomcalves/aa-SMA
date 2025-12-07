import random
import pickle
import os
from typing import Optional

from abstract.agent import AgentStatus
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from core.logger import log
from map.position import Position


class Phineas(Navigator2D):
    """
    Agente Híbrido:
    - Q-Learning para exploração (encontrar comida).
    - Navegação Heurística/Sensorial para retorno ao ninho.
    """

    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)

        self._position = Position(*properties.get("starting_position", (0, 0)))
        self.char = properties.get("char", "P")
        self.learning_rate = properties.get("learning_rate", 0.1)
        self.discount_factor = properties.get("discount_factor", 0.9)
        self.epsilon = properties.get("epsilon", 0.1)
        self.mode = properties.get("mode", "LEARNING")

        self.carrying = False
        self.q_table = {}
        self.visit_counts = {}

        # --- MEMÓRIA ESPACIAL ---
        self.known_nest_position: Optional[Position] = None

        self.last_state = None
        self.last_action = None
        self.last_attempted_action: Optional[Action] = None
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
        """ Verifica se o ninho está à volta e guarda a posição absoluta """
        for direction, content in cells.items():
            if content in ["NEST", "Nest"]:
                self.known_nest_position = self._position + direction

    def observation(self, obs: Observation):
        """ Recebe feedback e atualiza estado interno """
        if obs.type == ObservationType.ACCEPTED:
            self.last_extrinsic_reward = obs.payload.reward

            if self.last_attempted_action:
                if self.last_attempted_action.name == "move":
                    direction = self.last_attempted_action.params.get("direction")
                    if direction:
                        self._position = self._position + direction

                # 2. Atualiza estado de carga
                elif self.last_attempted_action.name == "pick":
                    self.carrying = True
                elif self.last_attempted_action.name == "drop":
                    self.carrying = False

        elif obs.type == ObservationType.DENIED:
            self.last_extrinsic_reward = obs.payload.reward

        elif obs.type == ObservationType.TERMINATE:
            self.last_extrinsic_reward = obs.payload.reward
            self.status = AgentStatus.TERMINATED
            self.save_knowledge()

    def _get_state_key(self) -> str:
        state_parts = [f"C:{1 if self.carrying else 0}"]
        obs_dir = self.curr_observations.get(ObservationType.DIRECTION)
        if obs_dir: state_parts.append(f"Dir:{obs_dir.payload.direction}")
        return ";".join(state_parts)

    def _learn(self, current_state: str):
        if self.last_state is None or self.last_action is None: return
        old_q = self.q_table.get((self.last_state, self.last_action), 0.0)

        # Novelty reward
        visit_bonus = 1.0 / (self.visit_counts.get(current_state, 0) + 1)
        r_total = self.last_extrinsic_reward + visit_bonus

        max_next_q = float('-inf')
        for move in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            q = self.q_table.get((current_state, str(move)), 0.0)
            if q > max_next_q: max_next_q = q
        if max_next_q == float('-inf'): max_next_q = 0.0

        new_q = old_q + self.learning_rate * (r_total + (self.discount_factor * max_next_q) - old_q)
        self.q_table[(self.last_state, self.last_action)] = new_q

    def _get_direction_to_target(self, target: Position, valid_moves: list) -> Direction:
        """ Calcula a melhor direção para o alvo (Manhattan) """
        diff = target - self._position
        dx, dy = diff.x, diff.y

        if abs(dx) > abs(dy):
            primary = Direction.RIGHT if dx > 0 else Direction.LEFT
            secondary = Direction.DOWN if dy > 0 else Direction.UP
        else:
            primary = Direction.DOWN if dy > 0 else Direction.UP
            secondary = Direction.RIGHT if dx > 0 else Direction.LEFT

        if primary in valid_moves: return primary
        if secondary in valid_moves: return secondary

        return random.choice(valid_moves) if valid_moves else Direction.NONE

    def act(self) -> Action:
        if not self.has_observations(): self.use_sensor()

        # 1. INSTINTO: Interagir (Pick/Drop)
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

        # 2. FILTRO DE MOVIMENTOS (CRÍTICO: Paredes são proibidas)
        valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)

        if obs_surr:
            # Lista exaustiva de nomes para paredes
            walls = ["WALL", "OBSTACLE", "Wall", "Obstacle", "#"]
            valid_moves = [d for d, c in obs_surr.payload.cells.items() if c not in walls]

        if not valid_moves:
            act = self.action.wait();
            self.last_attempted_action = act;
            return act

        # 3. DECISÃO DE NAVEGAÇÃO
        final_dir = None

        # --- FASE A: RETORNO AO NINHO (Se tiver carga) ---
        if self.carrying:
            # Opção A: Já sabemos onde é o ninho? Matemática pura.
            if self.known_nest_position:
                final_dir = self._get_direction_to_target(self.known_nest_position, valid_moves)

            # Opção B: Não sabemos, mas o sensor de direção (Environment Hack) aponta o caminho.
            elif ObservationType.DIRECTION in self.curr_observations:
                obs_dir = self.curr_observations[ObservationType.DIRECTION]
                # obs_dir.payload.direction é um tuplo de Directions: (DirX, DirY)
                dx, dy = obs_dir.payload.direction

                # Tenta seguir o sensor
                if dx != Direction.NONE and dx in valid_moves:
                    final_dir = dx
                elif dy != Direction.NONE and dy in valid_moves:
                    final_dir = dy

            # Se ainda não temos direção, explora aleatoriamente até achar pista
            if final_dir is None:
                final_dir = random.choice(valid_moves)

        # --- FASE B: PROCURA (Sem carga) - Q-Learning ---
        else:
            curr_state = self._get_state_key()
            self.visit_counts[curr_state] = self.visit_counts.get(curr_state, 0) + 1
            if self.mode == "LEARNING": self._learn(curr_state)

            if self.mode == "TEST" or random.random() > self.epsilon:
                # Exploit
                max_q = float('-inf')
                best = []
                for m in valid_moves:
                    q = self.q_table.get((curr_state, str(m)), 0.0)
                    if q > max_q:
                        max_q = q; best = [m]
                    elif q == max_q:
                        best.append(m)
                final_dir = random.choice(best) if best else random.choice(valid_moves)
            else:
                # Explore
                final_dir = random.choice(valid_moves)

        self.last_state = curr_state
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