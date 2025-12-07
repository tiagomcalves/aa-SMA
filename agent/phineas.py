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
    Agente Q-Learning com Recompensa Híbrida (Extrínseca + Intrínseca/Novelty).
    """

    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)

        # Configs
        self._position = Position(*properties.get("starting_position", (0, 0)))
        self.char = properties.get("char", "P")

        # Hiperparâmetros
        self.learning_rate = properties.get("learning_rate", 0.1)
        self.discount_factor = properties.get("discount_factor", 0.9)
        self.epsilon = properties.get("epsilon", 0.1)
        self.mode = properties.get("mode", "LEARNING")

        # Conhecimento
        self.q_table = {}
        self.visit_counts = {}  # Novelty Search Memory

        # Memória de Estado Anterior
        self.last_state: Optional[str] = None
        self.last_action: Optional[str] = None
        self.last_extrinsic_reward: float = 0.0

        self.load_knowledge()

    def use_sensor(self) -> Observation:
        obs = self._sensor.get_info(self)
        self.state.update_sensor_data(True, obs)

        # Mapeamento do Payload para uso interno
        if obs.surroundings:
            self.curr_observations[ObservationType.SURROUNDINGS] = obs.surroundings
        if obs.directions:
            self.curr_observations[ObservationType.DIRECTION] = obs.directions
        if obs.location:
            self.curr_observations[ObservationType.LOCATION] = obs.location

        return obs

    def observation(self, obs: Observation):
        if obs.type == ObservationType.ACCEPTED:
            # Recebe a recompensa do ambiente (ex: -1 por andar, +100 por objetivo)
            self.last_extrinsic_reward = obs.payload.reward

        elif obs.type == ObservationType.DENIED:
            # Se bateu na parede, penalização imediata
            self.last_extrinsic_reward = obs.payload.reward

        elif obs.type == ObservationType.TERMINATE:
            self.last_extrinsic_reward = obs.payload.reward  # +100 final
            self.status = AgentStatus.TERMINATED
            self.save_knowledge()
            log().print(f"Agente {self.name} terminou. Conhecimento salvo.")

    def _get_state_key(self) -> str:
        """ Gera hash do estado atual baseado nos sensores """
        state_parts = []

        # Sensor de Direção (Onde está o objetivo?)
        obs_dir = self.curr_observations.get(ObservationType.DIRECTION)
        if obs_dir:
            # Nota: obs_dir.payload.direction é um tuplo (DirX, DirY)
            state_parts.append(f"Dir:{obs_dir.payload.direction}")

        # Sensor de Arredores (Onde estão as paredes?)
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        if obs_surr:
            cells = obs_surr.payload.cells
            # Ordenar chaves para garantir consistência da string
            # Direction é Enum, ordenamos pelo 'name' ou 'value' se possível
            # Simplificação: assumindo chaves fixas
            surr_str = ""
            for d in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
                val = cells.get(d, "UNK")
                surr_str += f"{d.name[0]}:{val}|"
            state_parts.append(f"Surr:{surr_str}")

        return ";".join(state_parts)

    def _calculate_intrinsic_reward(self, state: str) -> float:
        """
        Novelty Search: Bónus por visitar estados novos.
        Opção A (Decaimento): 1.0 / N visitas (Incentiva exploração contínua)
        Opção B (Estrita): 1.0 se N=1, senão 0 (Apenas novidade absoluta)
        """
        count = self.visit_counts.get(state, 0)

        # Implementação com Decaimento (Mais estável para Q-Learning)
        if count == 0: return 1.0
        return 1.0 / (count + 1)

    def _learn(self, current_state: str):
        """ Algoritmo Q-Learning """
        if self.last_state is None or self.last_action is None:
            return

        old_q = self.q_table.get((self.last_state, self.last_action), 0.0)

        # R_total = R_extrinseca (Ambiente) + R_intrinseca (Novidade do estado atual)
        r_intrinsic = self._calculate_intrinsic_reward(current_state)
        r_total = self.last_extrinsic_reward + r_intrinsic

        # Max Q(S', a')
        max_next_q = float('-inf')
        possible_actions = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        for move in possible_actions:
            q_val = self.q_table.get((current_state, str(move)), 0.0)
            if q_val > max_next_q:
                max_next_q = q_val

        if max_next_q == float('-inf'): max_next_q = 0.0

        # Atualização Bellman
        new_q = old_q + self.learning_rate * (r_total + (self.discount_factor * max_next_q) - old_q)
        self.q_table[(self.last_state, self.last_action)] = new_q

    def act(self) -> Action:
        if not self.has_observations():
            self.use_sensor()

        current_state = self._get_state_key()

        # Update contagem de visitas
        self.visit_counts[current_state] = self.visit_counts.get(current_state, 0) + 1

        # Passo de Aprendizagem
        if self.mode == "LEARNING":
            self._learn(current_state)

        # Escolha da Ação
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        valid_moves = []
        if obs_surr:
            for direction, content in obs_surr.payload.cells.items():
                if content != "OBSTACLE" and content != "WALL":  # Ajustar string ao teu Entity Map
                    valid_moves.append(direction)
        else:
            valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        if not valid_moves:
            # Encurralado
            return self.action.wait()

        # Epsilon-Greedy
        chosen_direction = None

        if self.mode == "TEST" or random.random() > self.epsilon:
            # EXPLOIT (Melhor Q)
            max_q = float('-inf')
            best_moves = []
            for move in valid_moves:
                q = self.q_table.get((current_state, str(move)), 0.0)
                if q > max_q:
                    max_q = q
                    best_moves = [move]
                elif q == max_q:
                    best_moves.append(move)

            chosen_direction = random.choice(best_moves) if best_moves else random.choice(valid_moves)
        else:
            # EXPLORE (Aleatório)
            chosen_direction = random.choice(valid_moves)

        self.last_state = current_state
        self.last_action = str(chosen_direction)

        return self.action.move(chosen_direction)

    def save_knowledge(self):
        filename = f"qtable_{self.name}.pkl"
        try:
            with open(filename, "wb") as f:
                pickle.dump(self.q_table, f)
        except Exception:
            pass  # Ignorar erros de ficheiro no shutdown

    def load_knowledge(self):
        filename = f"qtable_{self.name}.pkl"
        if os.path.exists(filename):
            try:
                with open(filename, "rb") as f:
                    self.q_table = pickle.load(f)
                log().print(f"Q-Table loaded: {len(self.q_table)} states.")
            except Exception:
                pass