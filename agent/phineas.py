# agent/phineas.py
import random
import pickle
import os
from typing import Optional, Dict, Tuple
from collections import deque
from datetime import datetime

from abstract.agent import AgentStatus
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from core.logger import log
from map.position import Position


class Phineas(Navigator2D):
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)

        # POSIÇÃO E IDENTIFICAÇÃO
        self._position = Position(*properties.get("starting_position", (0, 0)))
        self.char = properties.get("char", "P")
        self.problem = problem

        # PARÂMETROS DE APRENDIZAGEM
        self.learning_rate = properties.get("learning_rate", 0.1)
        self.discount_factor = properties.get("discount_factor", 0.9)
        self.epsilon = properties.get("epsilon", 0.15)

        # MODO DO AGENTE (LEARNING ou TEST)
        self.mode = properties.get("mode", "LEARNING").upper()

        # Configuração do Logger
        if self.mode == "LEARNING":
            agent_config = {
                "learning_rate": self.learning_rate,
                "discount_factor": self.discount_factor,
                "epsilon": self.epsilon,
                "problem": problem
            }
            self.learning_logger = log().create_learning_logger(name, agent_config)
            log().print(f"🧠 {self.name}: MODO APRENDIZAGEM ATIVADO")
        else:
            self.epsilon = 0.0
            self.learning_rate = 0.0
            self.learning_logger = None
            log().print(f"🧪 {self.name}: MODO TESTE ATIVADO (política fixa)")

        # CONTROLE DE EPISÓDIOS
        self.current_episode = 0
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.episode_success = False

        # HISTÓRICO
        self.episode_rewards = []
        self.episode_steps_list = []
        self.episode_successes = []

        # ESTADO DO AGENTE
        self.carrying = False
        self.q_table = {}
        self.visit_counts = {}

        # CONTADORES
        self.total_food_collected = 0
        self.total_food_delivered = 0
        self.successful_returns = 0
        self.step_count = 0

        # SISTEMA DE COORDENADAS E MEMÓRIA
        # CORREÇÃO: Assume que nasce no ninho ou perto dele
        self.known_nest_position: Optional[Position] = self._position
        self.my_estimated_position = self._position  # Usa a posição inicial real
        self.has_position_reference = True

        # HISTÓRICO PARA APRENDIZAGEM
        self.last_state = None
        self.last_action = None
        self.last_attempted_action = None
        self.last_extrinsic_reward = 0.0

        # SISTEMA ANTI-LOOP
        self.pos_history = deque(maxlen=12)
        self.action_history = deque(maxlen=8)
        self.panic_mode = 0
        self.stuck_counter = 0

        # CARREGA CONHECIMENTO PRÉVIO
        self.load_knowledge()

    # ---------------------------------------------------
    # MÉTODOS DE CONTROLE DE EPISÓDIO
    # ---------------------------------------------------
    def start_episode(self):
        self.current_episode += 1
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.episode_success = False
        self.last_extrinsic_reward = 0.0
        # Reset parcial do estado para novo episódio, mas mantém conhecimento
        self.carrying = False
        self.panic_mode = 0
        self.stuck_counter = 0
        log().vprint(f"🚀 {self.name}: Iniciando Episódio {self.current_episode}")

    def register_reward(self, reward: float):
        self.episode_reward += reward
        self.episode_steps += 1
        self.last_extrinsic_reward = reward

    def end_episode(self, success: bool = False):
        self.episode_success = success
        self.episode_rewards.append(self.episode_reward)
        self.episode_steps_list.append(self.episode_steps)
        self.episode_successes.append(1 if success else 0)

        # Cálculo de médias
        avg_reward_last_10 = 0.0
        success_rate_last_10 = 0.0
        if len(self.episode_rewards) >= 10:
            avg_reward_last_10 = sum(self.episode_rewards[-10:]) / 10
            success_rate_last_10 = sum(self.episode_successes[-10:]) / 10

        # Registo no Logger
        if self.mode == "LEARNING" and self.learning_logger:
            episode_data = {
                'episode': self.current_episode,
                'total_reward': self.episode_reward,
                'steps': self.episode_steps,
                'success': success,
                'epsilon': self.epsilon,
                'successful_returns': self.successful_returns,
                'food_collected': self.total_food_collected,
                'food_delivered': self.total_food_delivered
            }
            self.learning_logger.log_episode(episode_data)
            if self.current_episode % 20 == 0:
                self.learning_logger.save_q_table(self.q_table)

        # Output TUI
        log().print(
            f"\n📊 {self.name}: EPISÓDIO {self.current_episode} (Sucesso: {success}) | Reward: {self.episode_reward:.1f}")

        if self.mode == "LEARNING":
            self.epsilon = max(0.01, self.epsilon * 0.995)  # Decay
            if self.current_episode % 10 == 0:
                self.save_knowledge()

    # ---------------------------------------------------
    # SENSORES E OBSERVAÇÕES
    # ---------------------------------------------------
    def use_sensor(self) -> Observation:
        obs = self._sensor.get_info(self)
        self.state.update_sensor_data(True, obs)
        self.step_count += 1

        if obs.surroundings:
            self.curr_observations[ObservationType.SURROUNDINGS] = obs.surroundings
            self._process_surroundings(obs.surroundings.payload.cells)

        if obs.directions:
            self.curr_observations[ObservationType.DIRECTION] = obs.directions

        if obs.location:
            self.curr_observations[ObservationType.LOCATION] = obs.location
            tile = getattr(obs.location.payload, 'tile_name', "").upper()
            if tile == "NEST":
                # Recalibra posição do ninho
                self.known_nest_position = self._position
                log().vprint(f"🎯 {self.name}: Recalibrei posição do NINHO: {self._position}")

        return obs

    def _update_sensor(self):
        self.curr_observations.clear()
        return self.use_sensor()

    def _process_surroundings(self, cells: dict):
        for direction, content in cells.items():
            if direction == Direction.NONE: continue

            content_upper = str(content).upper().strip()
            # Se vê ninho, guarda posição
            if content_upper in ["NEST", "N"]:
                self.known_nest_position = self._position + direction

    def observation(self, obs: Observation):
        """Processa o resultado da ação anterior"""
        if obs.type == ObservationType.ACCEPTED:
            reward = obs.payload.reward
            self.register_reward(reward)

            if self.last_attempted_action:
                if self.last_attempted_action.name == "move":
                    direction = self.last_attempted_action.params.get("direction")
                    if direction:
                        old_pos = self._position
                        self._position = self._position + direction
                        self.my_estimated_position = self._position  # Mantém sincronizado

                        self.pos_history.append(self._position)
                        self.action_history.append(str(direction))

                        if old_pos != self._position: self.stuck_counter = 0

                    # --- DETEÇÃO DE AUTO-PICKUP VIA REWARD ---
                    # Se o reward for alto (>40), significa que o ambiente fez auto-pickup ou auto-drop
                    if reward >= 40.0:
                        if not self.carrying:
                            self.carrying = True
                            self.total_food_collected += 1
                            log().print(f"✅ {self.name}: Apanhei comida! (Auto)")
                        else:
                            self.carrying = False
                            self.total_food_delivered += 1
                            self.successful_returns += 1
                            self.episode_success = True
                            log().print(f"🎉 {self.name}: Entreguei no Ninho! (Auto)")

                elif self.last_attempted_action.name == "pick":
                    self.carrying = True
                    self.total_food_collected += 1
                elif self.last_attempted_action.name == "drop":
                    self.carrying = False
                    self.total_food_delivered += 1
                    self.successful_returns += 1
                    self.episode_success = True

        elif obs.type == ObservationType.DENIED:
            self.stuck_counter += 1
            self.register_reward(-0.1)

        elif obs.type == ObservationType.TERMINATE:
            self.status = AgentStatus.TERMINATED
            success = self.total_food_delivered > 0
            self.end_episode(success)
            self.save_knowledge()

    # ---------------------------------------------------
    # LÓGICA PRINCIPAL (ACT)
    # ---------------------------------------------------
    def act(self) -> Action:
        self._update_sensor()

        # 1. AÇÕES IMEDIATAS (Se estiver em cima)
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

        # 2. FILTRO DE PAREDES
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        valid_moves = []
        if obs_surr:
            bad_tiles = ["#", "WALL", "OBSTACLE", "X", "W"]
            for d, c in obs_surr.payload.cells.items():
                if d != Direction.NONE and str(c).upper().strip() not in bad_tiles:
                    valid_moves.append(d)
        else:
            valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        if not valid_moves:
            act = self.action.wait();
            self.last_attempted_action = act;
            return act

        # 3. DETEÇÃO DE LOOP (PÂNICO)
        if self._is_stuck_in_loop() or self.stuck_counter > 3:
            self.panic_mode = 5
            self.stuck_counter = 0

        if self.panic_mode > 0:
            self.panic_mode -= 1
            final_dir = random.choice(valid_moves)
            act = self.action.move(final_dir);
            self.last_attempted_action = act;
            return act

        # ==============================================================
        # 4. LÓGICA INTELIGENTE DE MOVIMENTO
        # ==============================================================
        final_dir = None

        # --- CASO A: TENHO COMIDA -> VOLTAR AO NINHO ---
        if self.carrying:
            # Se tenho um ninho conhecido, vou para lá
            if self.known_nest_position:
                final_dir = self._calculate_best_direction(valid_moves)

            # Se não tenho, tento ir na direção oposta ao último movimento (backtrack)
            # ou uso heurística (geralmente ninho está no canto)
            if not final_dir:
                # Fallback: Tenta ir para Cima/Esquerda (heurística comum)
                preferred = [d for d in [Direction.UP, Direction.LEFT] if d in valid_moves]
                final_dir = random.choice(preferred) if preferred else random.choice(valid_moves)

        # --- CASO B: NÃO TENHO COMIDA -> PROCURAR ---
        else:
            # [CRÍTICO] VISÃO IMEDIATA: Se vejo comida ao lado, vou para lá!
            food_dir = self._scan_adjacent_food(valid_moves)
            if food_dir:
                final_dir = food_dir
            else:
                # Se não vejo comida, uso Q-Learning
                state = self._get_state_key()
                self.visit_counts[state] = self.visit_counts.get(state, 0) + 1

                if self.mode == "LEARNING" and self.last_state and self.last_action:
                    self._learn(state)

                if self.mode == "TEST":
                    final_dir = self._choose_best_q_action(state, valid_moves)
                else:
                    if random.random() > self.epsilon:
                        final_dir = self._choose_best_q_action(state, valid_moves)
                    else:
                        final_dir = random.choice(valid_moves)

                if self.mode == "LEARNING":
                    self.last_state = state
                    self.last_action = str(final_dir)

        # Segurança final
        if final_dir not in valid_moves:
            final_dir = random.choice(valid_moves)

        act = self.action.move(final_dir)
        self.last_attempted_action = act
        return act

    def _scan_adjacent_food(self, valid_moves: list) -> Optional[Direction]:
        """Procura comida nas células adjacentes e retorna a direção"""
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        if obs_surr:
            for direction, content in obs_surr.payload.cells.items():
                if direction in valid_moves:
                    if str(content).upper().strip() in ["FOOD", "RESOURCE", "F"]:
                        log().vprint(f"👀 {self.name}: Vi comida em {direction}! Indo pegar.")
                        return direction
        return None

    def _calculate_best_direction(self, valid_moves: list) -> Optional[Direction]:
        """Navegação por coordenadas para o ninho"""
        if not self.known_nest_position: return None

        dx = self.known_nest_position.x - self._position.x
        dy = self.known_nest_position.y - self._position.y

        # Prioriza o eixo com maior distância
        if abs(dx) > abs(dy):
            if dx > 0 and Direction.RIGHT in valid_moves: return Direction.RIGHT
            if dx < 0 and Direction.LEFT in valid_moves: return Direction.LEFT
            # Se eixo X bloqueado, tenta Y
            if dy > 0 and Direction.DOWN in valid_moves: return Direction.DOWN
            if dy < 0 and Direction.UP in valid_moves: return Direction.UP
        else:
            if dy > 0 and Direction.DOWN in valid_moves: return Direction.DOWN
            if dy < 0 and Direction.UP in valid_moves: return Direction.UP
            # Se eixo Y bloqueado, tenta X
            if dx > 0 and Direction.RIGHT in valid_moves: return Direction.RIGHT
            if dx < 0 and Direction.LEFT in valid_moves: return Direction.LEFT

        return random.choice(valid_moves)

    def _choose_best_q_action(self, state: str, valid_moves: list) -> Direction:
        best_q = float('-inf')
        best_actions = []
        for move in valid_moves:
            q = self.q_table.get((state, str(move)), 0.0)
            if q > best_q:
                best_q = q
                best_actions = [move]
            elif q == best_q:
                best_actions.append(move)
        return random.choice(best_actions) if best_actions else random.choice(valid_moves)

    def _is_stuck_in_loop(self) -> bool:
        if len(self.pos_history) < 6: return False
        recent = list(self.pos_history)[-6:]
        return len(set(recent)) <= 2

    # ---------------------------------------------------
    # ESTADO E APRENDIZAGEM
    # ---------------------------------------------------
    def _get_state_key(self) -> str:
        return f"C:{1 if self.carrying else 0}|Pos:{self._position.x},{self._position.y}"

    def _learn(self, current_state: str):
        if not self.last_state or not self.last_action: return
        old_q = self.q_table.get((self.last_state, self.last_action), 0.0)

        # Reward intrínseco (novidade)
        bonus = 0.5 / (self.visit_counts.get(current_state, 0) + 1)
        total_r = self.last_extrinsic_reward + bonus

        max_next_q = 0.0
        for move in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            q = self.q_table.get((current_state, str(move)), 0.0)
            max_next_q = max(max_next_q, q)

        new_q = old_q + self.learning_rate * (total_r + self.discount_factor * max_next_q - old_q)
        self.q_table[(self.last_state, self.last_action)] = new_q

    # ---------------------------------------------------
    # PERSISTÊNCIA
    # ---------------------------------------------------
    def save_knowledge(self):
        try:
            data = {
                'q_table': self.q_table,
                'visit_counts': self.visit_counts,
                'known_nest': (self.known_nest_position.x,
                               self.known_nest_position.y) if self.known_nest_position else None,
                'current_episode': self.current_episode,
                'epsilon': self.epsilon
            }
            with open(f"knowledge_{self.name}.pkl", "wb") as f:
                pickle.dump(data, f)
        except Exception:
            pass

    def load_knowledge(self):
        filename = f"knowledge_{self.name}.pkl"
        if os.path.exists(filename):
            try:
                with open(filename, "rb") as f:
                    data = pickle.load(f)
                self.q_table = data.get('q_table', {})
                self.visit_counts = data.get('visit_counts', {})
                self.current_episode = data.get('current_episode', 0)
                self.epsilon = data.get('epsilon', self.epsilon)
                if data.get('known_nest'):
                    self.known_nest_position = Position(*data['known_nest'])
            except Exception:
                pass