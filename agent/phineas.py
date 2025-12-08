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

        # PARÂMETROS DE APRENDIZAGEM (do properties ou padrão)
        self.learning_rate = properties.get("learning_rate", 0.1)
        self.discount_factor = properties.get("discount_factor", 0.9)
        self.epsilon = properties.get("epsilon", 0.15)

        # MODO DO AGENTE (LEARNING ou TEST)
        self.mode = properties.get("mode", "LEARNING").upper()

        # NOVO: Inicialização do logger de aprendizagem
        if self.mode == "LEARNING":
            # Configuração para o logger
            agent_config = {
                "learning_rate": self.learning_rate,
                "discount_factor": self.discount_factor,
                "epsilon": self.epsilon,
                "problem": problem
            }
            self.learning_logger = log().create_learning_logger(name, agent_config)
            log().print(f"🧠 {self.name}: MODO APRENDIZAGEM ATIVADO")
        else:
            # Modo TEST: usa política fixa
            self.epsilon = 0.0  # Sem exploração
            self.learning_rate = 0.0  # Sem aprendizagem
            self.learning_logger = None
            log().print(f"🧪 {self.name}: MODO TESTE ATIVADO (política fixa)")

        # CONTROLE DE EPISÓDIOS
        self.current_episode = 0
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.episode_success = False

        # HISTÓRICO PARA ANÁLISE
        self.episode_rewards = []  # Recompensa total por episódio
        self.episode_steps_list = []  # Passos por episódio
        self.episode_successes = []  # Sucesso por episódio (0 ou 1)

        # ESTADO DO AGENTE
        self.carrying = False
        self.q_table = {}
        self.visit_counts = {}

        # CONTADORES
        self.total_food_collected = 0
        self.total_food_delivered = 0
        self.successful_returns = 0
        self.step_count = 0

        # SISTEMA DE COORDENADAS SIMPLIFICADO
        self.known_nest_position: Optional[Position] = None
        self.my_estimated_position = Position(0, 0)
        self.has_position_reference = False
        self.position_offset = Position(0, 0)

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
        self.last_valid_moves = []

        # CARREGA CONHECIMENTO PRÉVIO
        self.load_knowledge()

        log().print(f"🤖 {self.name} inicializado:")
        log().print(f"   Posição: {self._position}")
        log().print(f"   Modo: {self.mode}")
        log().print(f"   Parâmetros: LR={self.learning_rate}, DF={self.discount_factor}, ε={self.epsilon}")

    # ---------------------------------------------------
    # MÉTODOS DE CONTROLE DE EPISÓDIO
    # ---------------------------------------------------
    def start_episode(self):
        """Inicia um novo episódio"""
        self.current_episode += 1
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.episode_success = False
        self.last_extrinsic_reward = 0.0

        log().vprint(f"🚀 {self.name}: Iniciando Episódio {self.current_episode}")

    def register_reward(self, reward: float):
        """Regista uma recompensa recebida"""
        self.episode_reward += reward
        self.episode_steps += 1
        self.last_extrinsic_reward = reward

        if abs(reward) > 0.1:  # Mostra apenas recompensas significativas
            log().vprint(f"💰 {self.name}: +{reward:.2f} (Total: {self.episode_reward:.2f})")

    def end_episode(self, success: bool = False):
        """Finaliza o episódio atual e regista dados"""
        self.episode_success = success

        # Guarda no histórico
        self.episode_rewards.append(self.episode_reward)
        self.episode_steps_list.append(self.episode_steps)
        self.episode_successes.append(1 if success else 0)

        # Calcula estatísticas dos últimos 10 episódios
        avg_reward_last_10 = 0.0
        success_rate_last_10 = 0.0

        if len(self.episode_rewards) >= 10:
            last_10_rewards = self.episode_rewards[-10:]
            last_10_successes = self.episode_successes[-10:]

            avg_reward_last_10 = sum(last_10_rewards) / len(last_10_rewards)
            success_rate_last_10 = sum(last_10_successes) / len(last_10_successes)

        # REGISTO NO LOGGER (apenas no modo LEARNING)
        if self.mode == "LEARNING" and self.learning_logger:
            episode_data = {
                'episode': self.current_episode,
                'total_reward': self.episode_reward,
                'steps': self.episode_steps,
                'success': success,
                'epsilon': self.epsilon,
                'learning_rate': self.learning_rate,
                'discount_factor': self.discount_factor,
                'q_table_size': len(self.q_table),
                'successful_returns': self.successful_returns,
                'food_collected': self.total_food_collected,
                'food_delivered': self.total_food_delivered,
                'avg_reward_last_10': avg_reward_last_10,
                'success_rate_last_10': success_rate_last_10
            }

            self.learning_logger.log_episode(episode_data)

            # Salva Q-table periodicamente
            if self.current_episode % 20 == 0:
                self.learning_logger.save_q_table(self.q_table)

        # LOG DO EPISÓDIO
        log().print(f"\n{'=' * 50}")
        log().print(f"📊 {self.name}: EPISÓDIO {self.current_episode} FINALIZADO")
        log().print(f"{'=' * 50}")
        log().print(f"✅ Sucesso: {'SIM' if success else 'NÃO'}")
        log().print(f"💰 Recompensa total: {self.episode_reward:.2f}")
        log().print(f"👣 Passos: {self.episode_steps}")
        log().print(f"🍎 Comida coletada: {self.total_food_collected}")
        log().print(f"🏠 Comida entregue: {self.total_food_delivered}")

        if self.mode == "LEARNING":
            # Decay do epsilon (reduz exploração ao longo do tempo)
            self.epsilon = max(0.01, self.epsilon * 0.995)

            log().print(f"🎲 ε atual: {self.epsilon:.3f}")

            if avg_reward_last_10 > 0:
                log().print(f"📈 Média (últimos 10): {avg_reward_last_10:.2f}")
                log().print(f"🎯 Taxa sucesso (últimos 10): {success_rate_last_10 * 100:.1f}%")

        # Guarda conhecimento periodicamente
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
                # Se está no ninho, esta é a posição REAL
                self.known_nest_position = self._position
                self.my_estimated_position = self._position
                self.has_position_reference = True
                log().vprint(f"🎯 {self.name}: Confirmado no NINHO!")

        return obs

    def _update_sensor(self):
        """Atualiza os sensores"""
        self.curr_observations.clear()
        obs = self.use_sensor()

        log().vprint(f"📍 {self.name}: Posição REAL: {self._position}")
        log().vprint(f"📍 {self.name}: Posição ESTIMADA: {self.my_estimated_position}")

        return obs

    def _process_surroundings(self, cells: dict):
        """Processa o que vê ao redor"""
        for direction, content in cells.items():
            if direction == Direction.NONE:
                continue

            content_upper = str(content).upper().strip()

            # Se vê ninho, calcula sua posição
            if content_upper in ["NEST", "N"] and not self.known_nest_position:
                self._calculate_nest_position(direction)

    def _calculate_nest_position(self, direction: Direction):
        """Calcula a posição do ninho baseado na direção vista"""
        if not self.has_position_reference:
            self.my_estimated_position = Position(0, 0)

        if direction == Direction.UP:
            nest_pos = Position(self.my_estimated_position.x, self.my_estimated_position.y - 1)
        elif direction == Direction.DOWN:
            nest_pos = Position(self.my_estimated_position.x, self.my_estimated_position.y + 1)
        elif direction == Direction.LEFT:
            nest_pos = Position(self.my_estimated_position.x - 1, self.my_estimated_position.y)
        elif direction == Direction.RIGHT:
            nest_pos = Position(self.my_estimated_position.x + 1, self.my_estimated_position.y)
        else:
            return

        self.known_nest_position = nest_pos
        log().vprint(f"👀 {self.name}: Viu ninho em {direction}")

    def observation(self, obs: Observation):
        """Processa observações do ambiente"""
        if obs.type == ObservationType.ACCEPTED:
            reward = obs.payload.reward
            self.register_reward(reward)

            if self.last_attempted_action:
                if self.last_attempted_action.name == "move":
                    direction = self.last_attempted_action.params.get("direction")
                    if direction:
                        old_pos = self._position
                        self._position = self._position + direction

                        # Atualiza posição estimada
                        self._update_estimated_position(direction)

                        self.pos_history.append(self._position)
                        self.action_history.append(str(direction))

                        if old_pos != self._position:
                            self.stuck_counter = 0

                    # Detecção automática de pickup/drop
                    if reward >= 40.0:
                        if not self.carrying:
                            self.carrying = True
                            self.total_food_collected += 1
                            log().print(f"✅ {self.name}: Pegou comida! Total: {self.total_food_collected}")

                            if self.known_nest_position:
                                self._log_navigation_info()
                        else:
                            self.carrying = False
                            self.total_food_delivered += 1
                            self.successful_returns += 1
                            log().print(f"🎉 {self.name}: Depositou no ninho! Entregues: {self.total_food_delivered}")
                            self.episode_success = True

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
            self.register_reward(-0.1)  # Penalidade por ação negada

            if self.last_attempted_action and self.last_attempted_action.name == "move":
                blocked_dir = self.last_attempted_action.params.get("direction")
                log().vprint(f"❌ {self.name}: Movimento negado: {blocked_dir}")

        elif obs.type == ObservationType.TERMINATE:
            self.status = AgentStatus.TERMINATED

            # Finaliza o episódio
            success = self.total_food_delivered > 0
            self.end_episode(success)

            # Salva conhecimento final
            self.save_knowledge()

    def _update_estimated_position(self, direction: Direction):
        """Atualiza posição estimada baseada no movimento"""
        if direction == Direction.UP:
            self.my_estimated_position = Position(
                self.my_estimated_position.x,
                self.my_estimated_position.y - 1
            )
        elif direction == Direction.DOWN:
            self.my_estimated_position = Position(
                self.my_estimated_position.x,
                self.my_estimated_position.y + 1
            )
        elif direction == Direction.LEFT:
            self.my_estimated_position = Position(
                self.my_estimated_position.x - 1,
                self.my_estimated_position.y
            )
        elif direction == Direction.RIGHT:
            self.my_estimated_position = Position(
                self.my_estimated_position.x + 1,
                self.my_estimated_position.y
            )

    # ---------------------------------------------------
    # LÓGICA PRINCIPAL (ACT)
    # ---------------------------------------------------
    def act(self) -> Action:
        # Atualiza sensores
        self._update_sensor()

        # 1. AÇÕES DIRETAS (pick/drop)
        obs_loc = self.curr_observations.get(ObservationType.LOCATION)
        if obs_loc:
            tile = getattr(obs_loc.payload, 'tile_name', "").upper()
            if not self.carrying and tile in ["FOOD", "RESOURCE"]:
                act = self.action.pick()
                self.last_attempted_action = act
                return act
            if self.carrying and tile == "NEST":
                act = self.action.drop()
                self.last_attempted_action = act
                return act

        # 2. OBTÉM MOVIMENTOS VÁLIDOS
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        valid_moves = []

        if obs_surr:
            bad_tiles = ["#", "WALL", "wall", "OBSTACLE", "X", "W"]
            cells = obs_surr.payload.cells

            for direction, content in cells.items():
                if direction == Direction.NONE:
                    continue

                content_clean = str(content).strip()
                is_wall = content_clean in bad_tiles or content_clean.upper() in bad_tiles

                if not is_wall:
                    valid_moves.append(direction)
        else:
            valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        if not valid_moves:
            log().vprint(f"⚠️ {self.name}: Sem movimentos válidos! Esperando...")
            act = self.action.wait()
            self.last_attempted_action = act
            return act

        log().vprint(f"🔄 {self.name}: Movimentos válidos: {[str(m) for m in valid_moves]}")

        # 3. DETECÇÃO DE LOOP
        if self._is_stuck_in_loop() or self.stuck_counter > 3:
            log().print(f"🚨 {self.name}: LOOP DETECTADO! Modo pânico ativado")
            self.panic_mode = 5
            self.stuck_counter = 0

        # 4. MODO PÂNICO (movimento aleatório)
        if self.panic_mode > 0:
            self.panic_mode -= 1
            final_dir = random.choice(valid_moves)
            log().vprint(f"🌀 {self.name}: Modo pânico: {final_dir}")

        # 5. MODO CARRYING (VOLTA AO NINHO)
        elif self.carrying:
            log().vprint(f"🍎 {self.name}: TENHO COMIDA! Voltando ao ninho...")

            # Verifica se vê ninho ao lado
            nest_direction = None
            if obs_surr:
                for direction, content in obs_surr.payload.cells.items():
                    content_upper = str(content).upper().strip()
                    if content_upper in ["NEST", "N"] and direction in valid_moves:
                        nest_direction = direction
                        break

            if nest_direction:
                log().vprint(f"🎯 {self.name}: NINHO VISÍVEL! Indo direto...")
                final_dir = nest_direction
            else:
                # Navegação por coordenadas
                best_dir = self._calculate_best_direction(valid_moves)

                if best_dir:
                    final_dir = best_dir
                    log().vprint(f"🧭 {self.name}: Navegação por coordenadas: {final_dir}")
                else:
                    # Fallback inteligente
                    final_dir = self._choose_direction_with_q(valid_moves, "CARRYING")

        # 6. MODO EXPLORAÇÃO/APRENDIZAGEM
        else:
            state = self._get_state_key()
            self.visit_counts[state] = self.visit_counts.get(state, 0) + 1

            # APRENDIZAGEM Q-LEARNING (apenas no modo LEARNING)
            if self.mode == "LEARNING" and self.last_state and self.last_action:
                self._learn(state)

            # ESCOLHA DA AÇÃO
            # Modo TEST: sempre escolhe melhor ação (sem exploração)
            # Modo LEARNING: epsilon-greedy
            if self.mode == "TEST":
                final_dir = self._choose_best_q_action(state, valid_moves)
            else:
                if random.random() > self.epsilon:
                    final_dir = self._choose_best_q_action(state, valid_moves)
                else:
                    final_dir = random.choice(valid_moves)

            # Guarda estado para próximo aprendizado (apenas no modo LEARNING)
            if self.mode == "LEARNING":
                self.last_state = state
                self.last_action = str(final_dir)

        # VERIFICAÇÃO FINAL
        if final_dir not in valid_moves:
            log().vprint(f"⚠️ {self.name}: Direção inválida! Corrigindo...")
            final_dir = random.choice(valid_moves)

        # Cria ação
        act = self.action.move(final_dir)
        self.last_attempted_action = act
        return act

    def _choose_best_q_action(self, state: str, valid_moves: list) -> Direction:
        """Escolhe a melhor ação baseada na Q-table"""
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

    def _choose_direction_with_q(self, valid_moves: list, context: str = "") -> Direction:
        """Escolhe direção usando Q-table com contexto"""
        if context == "CARRYING" and self.known_nest_position:
            # Tenta ir na direção do ninho
            dx = self.known_nest_position.x - self.my_estimated_position.x
            dy = self.known_nest_position.y - self.my_estimated_position.y

            preferred = []
            if dx > 0 and Direction.RIGHT in valid_moves:
                preferred.append(Direction.RIGHT)
            elif dx < 0 and Direction.LEFT in valid_moves:
                preferred.append(Direction.LEFT)
            if dy > 0 and Direction.DOWN in valid_moves:
                preferred.append(Direction.DOWN)
            elif dy < 0 and Direction.UP in valid_moves:
                preferred.append(Direction.UP)

            if preferred:
                return random.choice(preferred)

        # Fallback para Q-table ou aleatório
        state = self._get_state_key()
        return self._choose_best_q_action(state, valid_moves)

    # ---------------------------------------------------
    # NAVEGAÇÃO
    # ---------------------------------------------------
    def _get_state_key(self) -> str:
        return f"C:{1 if self.carrying else 0}|Pos:{self._position.x},{self._position.y}"

    def _calculate_best_direction(self, valid_moves: list) -> Optional[Direction]:
        """Calcula a melhor direção baseada em coordenadas"""
        if not self.known_nest_position or not valid_moves:
            return None

        dx = self.known_nest_position.x - self.my_estimated_position.x
        dy = self.known_nest_position.y - self.my_estimated_position.y

        # Decide qual eixo priorizar
        if abs(dx) > abs(dy):
            if dx > 0 and Direction.RIGHT in valid_moves:
                return Direction.RIGHT
            elif dx < 0 and Direction.LEFT in valid_moves:
                return Direction.LEFT
        else:
            if dy > 0 and Direction.DOWN in valid_moves:
                return Direction.DOWN
            elif dy < 0 and Direction.UP in valid_moves:
                return Direction.UP

        # Fallback
        if abs(dx) > abs(dy):
            if dy > 0 and Direction.DOWN in valid_moves:
                return Direction.DOWN
            elif dy < 0 and Direction.UP in valid_moves:
                return Direction.UP
        else:
            if dx > 0 and Direction.RIGHT in valid_moves:
                return Direction.RIGHT
            elif dx < 0 and Direction.LEFT in valid_moves:
                return Direction.LEFT

        return None

    def _log_navigation_info(self):
        """Mostra informações de navegação"""
        if not self.known_nest_position:
            return

        dx = self.known_nest_position.x - self.my_estimated_position.x
        dy = self.known_nest_position.y - self.my_estimated_position.y

        log().vprint(f"🧭 {self.name}: Distância ao ninho: ({dx}, {dy})")

    def _is_stuck_in_loop(self) -> bool:
        """Detecta se o agente está em loop"""
        if len(self.pos_history) < 6:
            return False

        recent = list(self.pos_history)[-6:]
        if len(set(recent)) <= 2:
            return True

        if len(self.action_history) >= 4:
            actions = list(self.action_history)[-4:]
            if (actions[0] == actions[2] and actions[1] == actions[3] and actions[0] != actions[1]):
                return True

        if self.stuck_counter >= 3:
            return True

        return False

    # ---------------------------------------------------
    # APRENDIZAGEM Q-LEARNING
    # ---------------------------------------------------
    def _learn(self, current_state: str):
        """Atualiza Q-table usando Q-learning"""
        if not self.last_state or not self.last_action:
            return

        old_q = self.q_table.get((self.last_state, self.last_action), 0.0)

        # Recompensa intrínseca (encoraja exploração)
        exploration_bonus = 0.5 / (self.visit_counts.get(current_state, 0) + 1)
        total_reward = self.last_extrinsic_reward + exploration_bonus

        # Melhor Q do próximo estado
        max_next_q = 0.0
        for move in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            q = self.q_table.get((current_state, str(move)), 0.0)
            max_next_q = max(max_next_q, q)

        # Atualização Q-learning
        new_q = old_q + self.learning_rate * (
                total_reward + self.discount_factor * max_next_q - old_q
        )

        self.q_table[(self.last_state, self.last_action)] = new_q

        log().vprint(f"🧠 {self.name}: Q[{self.last_state}, {self.last_action}] = "
                     f"{old_q:.3f} → {new_q:.3f} (r={total_reward:.3f})")

    # ---------------------------------------------------
    # PERSISTÊNCIA
    # ---------------------------------------------------
    def save_knowledge(self):
        """Salva Q-table e conhecimento do agente"""
        try:
            data = {
                'q_table': self.q_table,
                'visit_counts': self.visit_counts,
                'known_nest': (self.known_nest_position.x, self.known_nest_position.y)
                if self.known_nest_position else None,
                'estimated_position': (self.my_estimated_position.x, self.my_estimated_position.y),
                'successful_returns': self.successful_returns,
                'total_food_collected': self.total_food_collected,
                'total_food_delivered': self.total_food_delivered,
                'total_rewards': self.episode_rewards,
                'episode_successes': self.episode_successes,
                'current_episode': self.current_episode,
                'epsilon': self.epsilon
            }

            filename = f"knowledge_{self.name}.pkl"
            with open(filename, "wb") as f:
                pickle.dump(data, f)

            log().vprint(f"💾 {self.name}: Conhecimento salvo em {filename}")

        except Exception as e:
            log().print(f"❌ {self.name}: Erro ao salvar conhecimento: {e}")

    def load_knowledge(self):
        """Carrega conhecimento prévio do agente"""
        filename = f"knowledge_{self.name}.pkl"

        if os.path.exists(filename):
            try:
                with open(filename, "rb") as f:
                    data = pickle.load(f)

                self.q_table = data.get('q_table', {})
                self.visit_counts = data.get('visit_counts', {})
                self.successful_returns = data.get('successful_returns', 0)
                self.total_food_collected = data.get('total_food_collected', 0)
                self.total_food_delivered = data.get('total_food_delivered', 0)
                self.episode_rewards = data.get('total_rewards', [])
                self.episode_successes = data.get('episode_successes', [])
                self.current_episode = data.get('current_episode', 0)
                self.epsilon = data.get('epsilon', self.epsilon)

                nest_pos = data.get('known_nest')
                if nest_pos:
                    self.known_nest_position = Position(*nest_pos)

                est_pos = data.get('estimated_position', (0, 0))
                self.my_estimated_position = Position(*est_pos)

                log().print(f"📂 {self.name}: Conhecimento carregado (Episódio {self.current_episode})")
                log().print(f"   Q-table: {len(self.q_table)} estados")

                if self.episode_rewards:
                    avg_reward = sum(self.episode_rewards) / len(self.episode_rewards)
                    log().print(f"   Recompensa média histórica: {avg_reward:.2f}")

            except Exception as e:
                log().print(f"❌ {self.name}: Erro ao carregar conhecimento: {e}")