import random
import pickle
import os
from typing import Optional, Dict, Tuple
from collections import deque

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

        self._position = Position(*properties.get("starting_position", (0, 0)))
        self.char = properties.get("char", "P")
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.15
        self.mode = properties.get("mode", "LEARNING")

        self.carrying = False
        self.q_table = {}
        self.visit_counts = {}

        # SISTEMA DE COORDENADAS SIMPLIFICADO
        self.known_nest_position: Optional[Position] = None
        self.my_estimated_position = Position(0, 0)  # Começa na origem
        self.has_position_reference = False
        self.position_offset = Position(0, 0)  # Offset para converter posições relativas

        # Histórico simples
        self.last_state = None
        self.last_action = None
        self.last_attempted_action = None
        self.last_extrinsic_reward = 0.0

        # Sistema Anti-Loop
        self.pos_history = deque(maxlen=12)
        self.action_history = deque(maxlen=8)
        self.panic_mode = 0
        self.stuck_counter = 0
        self.last_valid_moves = []

        # Contadores
        self.step_count = 0
        self.successful_returns = 0

        self.load_knowledge()

    # ---------------------------------------------------
    # SENSORES SIMPLIFICADOS
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
                # IMPORTANTE: Se está no ninho, esta é a posição REAL
                self.known_nest_position = self._position
                self.my_estimated_position = self._position
                self.has_position_reference = True
                log().print(f"[{self.name}] 🎯 CONFIRMADO no NINHO! Posição real: {self._position}")

        return obs

    def _update_sensor(self):
        """Atualiza os sensores OBRIGATORIAMENTE"""
        # Limpa observações antigas
        self.curr_observations.clear()

        # Pega informação atual
        obs = self.use_sensor()

        # Debug: mostra posição REAL vs estimada
        log().print(f"[{self.name}] 📍 POSIÇÃO REAL: {self._position}")
        log().print(f"[{self.name}] 📍 Posição ESTIMADA: {self.my_estimated_position}")

        return obs

    def _process_surroundings(self, cells: dict):
        """Processa o que vê ao redor de forma SIMPLES"""
        for direction, content in cells.items():
            if direction == Direction.NONE:
                continue

            content_upper = str(content).upper().strip()

            # Se vê ninho, calcula sua posição baseada na direção
            if content_upper in ["NEST", "N"] and not self.known_nest_position:
                self._calculate_nest_position(direction)

    def _calculate_nest_position(self, direction: Direction):
        """Calcula a posição do ninho baseado na direção vista"""
        # Se não temos referência, assumimos que começamos em (0,0)
        if not self.has_position_reference:
            self.my_estimated_position = Position(0, 0)

        # Calcula onde o ninho deve estar
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
        log().print(f"[{self.name}] 👀 Viu ninho em {direction}")
        log().print(f"    Minha posição estimada: {self.my_estimated_position}")
        log().print(f"    Ninho calculado em: {nest_pos}")

    def observation(self, obs: Observation):
        if obs.type == ObservationType.ACCEPTED:
            self.last_extrinsic_reward = obs.payload.reward

            if self.last_attempted_action:
                if self.last_attempted_action.name == "move":
                    direction = self.last_attempted_action.params.get("direction")
                    if direction:
                        old_pos = self._position
                        self._position = self._position + direction

                        # ATUALIZA POSIÇÃO ESTIMADA (sempre!)
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

                        self.pos_history.append(self._position)
                        self.action_history.append(str(direction))

                        if old_pos != self._position:
                            self.stuck_counter = 0
                            log().print(f"[{self.name}] Movimento aceito para {direction}")
                            log().print(f"    Posição estimada atualizada: {self.my_estimated_position}")

                    # Auto-Pickup Detection
                    if obs.payload.reward >= 40.0:
                        if not self.carrying:
                            self.carrying = True
                            log().print(f"[{self.name}] ✅ Pegou comida!")
                            log().print(f"    Posição estimada: {self.my_estimated_position}")

                            # Calcula rota para o ninho se souber onde está
                            if self.known_nest_position:
                                self._log_navigation_info()
                        else:
                            self.carrying = False
                            self.successful_returns += 1
                            log().print(f"[{self.name}] 🎉 Depositou no ninho! Total: {self.successful_returns}")

                elif self.last_attempted_action.name == "pick":
                    self.carrying = True
                elif self.last_attempted_action.name == "drop":
                    self.carrying = False

        elif obs.type == ObservationType.DENIED:
            self.stuck_counter += 1
            if self.last_attempted_action and self.last_attempted_action.name == "move":
                blocked_dir = self.last_attempted_action.params.get("direction")
                log().print(f"[{self.name}] ❌ Movimento negado: {blocked_dir}")

        elif obs.type == ObservationType.TERMINATE:
            self.status = AgentStatus.TERMINATED
            self.save_knowledge()

    def _log_navigation_info(self):
        """Mostra informações de navegação"""
        if not self.known_nest_position:
            return

        dx = self.known_nest_position.x - self.my_estimated_position.x
        dy = self.known_nest_position.y - self.my_estimated_position.y

        log().print(f"[{self.name}] 🧭 INFORMAÇÕES DE NAVEGAÇÃO:")
        log().print(f"    Posição estimada: {self.my_estimated_position}")
        log().print(f"    Ninho conhecido: {self.known_nest_position}")
        log().print(f"    Distância: ({dx}, {dy})")

        # Sugere direção ideal
        if abs(dx) > abs(dy):
            if dx > 0:
                log().print(f"    ➡️  Deve ir para RIGHT ({dx} unidades)")
            else:
                log().print(f"    ⬅️  Deve ir para LEFT ({-dx} unidades)")
        else:
            if dy > 0:
                log().print(f"    ⬇️  Deve ir para DOWN ({dy} unidades)")
            else:
                log().print(f"    ⬆️  Deve ir para UP ({-dy} unidades)")

    # ---------------------------------------------------
    # NAVEGAÇÃO INTELIGENTE
    # ---------------------------------------------------
    def _get_state_key(self) -> str:
        return f"C:{1 if self.carrying else 0}|Pos:{self._position.x},{self._position.y}"

    def _calculate_best_direction(self, valid_moves: list) -> Optional[Direction]:
        """Calcula a melhor direção baseada em coordenadas"""
        if not self.known_nest_position or not valid_moves:
            return None

        dx = self.known_nest_position.x - self.my_estimated_position.x
        dy = self.known_nest_position.y - self.my_estimated_position.y

        log().print(f"[{self.name}] 📐 Calculando rota:")
        log().print(f"    De: {self.my_estimated_position}")
        log().print(f"    Para: {self.known_nest_position}")
        log().print(f"    Diferença: dx={dx}, dy={dy}")

        # Decide qual eixo priorizar
        if abs(dx) > abs(dy):
            # Prioriza horizontal
            if dx > 0 and Direction.RIGHT in valid_moves:
                log().print(f"    🎯 Escolhendo RIGHT (fecha {dx} em X)")
                return Direction.RIGHT
            elif dx < 0 and Direction.LEFT in valid_moves:
                log().print(f"    🎯 Escolhendo LEFT (fecha {-dx} em X)")
                return Direction.LEFT
        else:
            # Prioriza vertical
            if dy > 0 and Direction.DOWN in valid_moves:
                log().print(f"    🎯 Escolhendo DOWN (fecha {dy} em Y)")
                return Direction.DOWN
            elif dy < 0 and Direction.UP in valid_moves:
                log().print(f"    🎯 Escolhendo UP (fecha {-dy} em Y)")
                return Direction.UP

        # Se não pode ir na direção ideal, tenta a outra dimensão
        if abs(dx) > abs(dy):
            # Tenta vertical como fallback
            if dy > 0 and Direction.DOWN in valid_moves:
                log().print(f"    🔄 Fallback: DOWN (fecha {dy} em Y)")
                return Direction.DOWN
            elif dy < 0 and Direction.UP in valid_moves:
                log().print(f"    🔄 Fallback: UP (fecha {-dy} em Y)")
                return Direction.UP
        else:
            # Tenta horizontal como fallback
            if dx > 0 and Direction.RIGHT in valid_moves:
                log().print(f"    🔄 Fallback: RIGHT (fecha {dx} em X)")
                return Direction.RIGHT
            elif dx < 0 and Direction.LEFT in valid_moves:
                log().print(f"    🔄 Fallback: LEFT (fecha {-dx} em X)")
                return Direction.LEFT

        return None

    # Sugestão de melhoria no sistema anti-loop:
    def _is_stuck_in_loop(self) -> bool:
        """Detecta loops com mais sensibilidade"""
        if len(self.pos_history) < 6:
            return False

        recent = list(self.pos_history)[-6:]

        # 1. Poucas posições únicas
        if len(set(recent)) <= 2:
            return True

        # 2. Padrão oscilatório (ex: RIGHT-LEFT-RIGHT-LEFT)
        if len(self.action_history) >= 4:
            actions = list(self.action_history)[-4:]
            if (actions[0] == actions[2] and
                    actions[1] == actions[3] and
                    actions[0] != actions[1]):
                return True

        # 3. Muitas tentativas negadas seguidas
        if self.stuck_counter >= 3:
            return True

        return False

    # ---------------------------------------------------
    # ACT - LOGICA PRINCIPAL CORRIGIDA
    # ---------------------------------------------------
    def act(self) -> Action:

        self._update_sensor()

        # 1. AÇÕES INSTINTIVAS (Pick/Drop)
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

        # 2. FILTRO DE PAREDES (CRÍTICO!)
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

            # Debug: mostra o que vê
            log().print(f"[{self.name}] 👀 Vê: { {str(k): v for k, v in cells.items()} }")
        else:
            valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        if not valid_moves:
            log().print(f"[{self.name}] ⚠️ Sem movimentos válidos! Esperando...")
            act = self.action.wait()
            self.last_attempted_action = act
            return act

        log().print(f"[{self.name}] Movimentos válidos: {[str(m) for m in valid_moves]}")

        # 3. DETECÇÃO DE LOOP
        if self._is_stuck_in_loop() or self.stuck_counter > 3:
            log().print(f"[{self.name}] 🚨 LOOP DETECTADO! Modo pânico ativado")
            self.panic_mode = 5
            self.stuck_counter = 0

        # 4. MODO PÂNICO (movimento aleatório)
        if self.panic_mode > 0:
            self.panic_mode -= 1
            final_dir = random.choice(valid_moves)
            log().print(f"[{self.name}] 🌀 Modo pânico: {final_dir}")

        # 5. MODO CARRYING (VOLTA AO NINHO)
        elif self.carrying:
            log().print(f"[{self.name}] 🍎 TENHO COMIDA! Voltando ao ninho...")

            # Verifica se sensor diz que ninho está ao lado
            nest_direction = None
            if obs_surr:
                for direction, content in obs_surr.payload.cells.items():
                    content_upper = str(content).upper().strip()
                    if content_upper in ["NEST", "N"] and direction in valid_moves:
                        nest_direction = direction
                        break

            # Se vê ninho ao lado E pode ir para lá, vai direto
            if nest_direction:
                log().print(f"[{self.name}] 🎯 NINHO VISÍVEL em {nest_direction}! Indo direto...")
                final_dir = nest_direction
            else:
                # Navegação por coordenadas
                best_dir = self._calculate_best_direction(valid_moves)

                if best_dir:
                    final_dir = best_dir
                    log().print(f"[{self.name}] 🧭 Navegação por coordenadas: {final_dir}")
                else:
                    # Fallback: movimento aleatório mas inteligente
                    if self.known_nest_position:
                        # Tenta ir na direção geral do ninho
                        dx = self.known_nest_position.x - self.my_estimated_position.x
                        dy = self.known_nest_position.y - self.my_estimated_position.y

                        preferred_dirs = []
                        if dx > 0 and Direction.RIGHT in valid_moves:
                            preferred_dirs.append(Direction.RIGHT)
                        elif dx < 0 and Direction.LEFT in valid_moves:
                            preferred_dirs.append(Direction.LEFT)
                        if dy > 0 and Direction.DOWN in valid_moves:
                            preferred_dirs.append(Direction.DOWN)
                        elif dy < 0 and Direction.UP in valid_moves:
                            preferred_dirs.append(Direction.UP)

                        if preferred_dirs:
                            final_dir = random.choice(preferred_dirs)
                            log().print(f"[{self.name}] ⚡ Direção preferencial: {final_dir}")
                        else:
                            final_dir = random.choice(valid_moves)
                            log().print(f"[{self.name}] 🎲 Escolha aleatória: {final_dir}")
                    else:
                        # Não sabe onde está o ninho
                        final_dir = random.choice(valid_moves)
                        log().print(f"[{self.name}] ❓ Ninho desconhecido. Aleatório: {final_dir}")

        # 6. MODO EXPLORAÇÃO (Q-Learning)
        else:
            state = self._get_state_key()
            self.visit_counts[state] = self.visit_counts.get(state, 0) + 1

            # Aprendizagem
            if self.mode == "LEARNING" and self.last_state and self.last_action:
                self._learn(state)

            # Escolha da ação
            if self.mode == "TEST" or random.random() > self.epsilon:
                # Exploração baseada em Q-table
                best_q = float('-inf')
                best_actions = []

                for move in valid_moves:
                    q = self.q_table.get((state, str(move)), 0.0)
                    if q > best_q:
                        best_q = q
                        best_actions = [move]
                    elif q == best_q:
                        best_actions.append(move)

                final_dir = random.choice(best_actions) if best_actions else random.choice(valid_moves)
            else:
                # Exploração aleatória
                final_dir = random.choice(valid_moves)

        # VERIFICAÇÃO FINAL DE SEGURANÇA
        if final_dir not in valid_moves:
            log().print(f"[{self.name}] ⚠️ Direção {final_dir} inválida! Corrigindo...")
            final_dir = random.choice(valid_moves)

        # Atualiza estado para Q-learning
        if not self.carrying:
            self.last_state = self._get_state_key()
            self.last_action = str(final_dir)

        # Cria ação
        act = self.action.move(final_dir)
        self.last_attempted_action = act
        return act

    # ---------------------------------------------------
    # MÉTODOS DE APRENDIZAGEM
    # ---------------------------------------------------
    def _learn(self, current_state: str):
        if not self.last_state or not self.last_action:
            return

        old_q = self.q_table.get((self.last_state, self.last_action), 0.0)

        # Recompensa ajustada
        bonus = 1.0 / (self.visit_counts.get(current_state, 0) + 1)
        total_r = self.last_extrinsic_reward + bonus

        # Encontra melhor Q do próximo estado
        max_next = 0.0
        for move in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            q = self.q_table.get((current_state, str(move)), 0.0)
            if q > max_next:
                max_next = q

        # Atualiza Q-value
        new_q = old_q + self.learning_rate * (total_r + self.discount_factor * max_next - old_q)
        self.q_table[(self.last_state, self.last_action)] = new_q

    # ---------------------------------------------------
    # PERSISTÊNCIA
    # ---------------------------------------------------
    def save_knowledge(self):
        try:
            data = {
                'q_table': self.q_table,
                'visit_counts': self.visit_counts,
                'known_nest': (self.known_nest_position.x, self.known_nest_position.y)
                if self.known_nest_position else None,
                'estimated_position': (self.my_estimated_position.x, self.my_estimated_position.y),
                'successful_returns': self.successful_returns
            }
            with open(f"qtable_{self.name}.pkl", "wb") as f:
                pickle.dump(data, f)
            log().print(f"[{self.name}] 💾 Conhecimento salvo!")
        except Exception as e:
            log().print(f"[{self.name}] ❌ Erro ao salvar: {e}")

    def load_knowledge(self):
        if os.path.exists(f"qtable_{self.name}.pkl"):
            try:
                with open(f"qtable_{self.name}.pkl", "rb") as f:
                    data = pickle.load(f)
                    self.q_table = data.get('q_table', {})
                    self.visit_counts = data.get('visit_counts', {})

                    nest_pos = data.get('known_nest')
                    if nest_pos:
                        self.known_nest_position = Position(*nest_pos)

                    est_pos = data.get('estimated_position', (0, 0))
                    self.my_estimated_position = Position(*est_pos)

                    self.successful_returns = data.get('successful_returns', 0)

                log().print(f"[{self.name}] 📂 Conhecimento carregado!")
                log().print(f"    Posição estimada: {self.my_estimated_position}")
                if self.known_nest_position:
                    log().print(f"    Ninho conhecido: {self.known_nest_position}")
            except Exception as e:
                log().print(f"[{self.name}] ❌ Erro ao carregar: {e}")