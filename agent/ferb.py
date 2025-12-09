import random
from collections import deque
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from core.logger import log
from map.position import Position


class Ferb(Navigator2D):
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)

        self._position = Position(*properties.get("starting_position", (0, 0)))
        self.char = properties.get("char", "F")

        # Sistema de navegação
        self.known_nest_position = None
        self.my_estimated_position = Position(0, 0)
        self.has_seen_nest = False

        # Estado
        self.carrying = False
        self.last_attempted_action = None
        self.last_extrinsic_reward = 0.0

        # Sistema Anti-Loop
        self.pos_history = deque(maxlen=10)
        self.action_history = deque(maxlen=8)
        self.panic_mode = 0
        self.stuck_counter = 0

        # Inércia para política fixa
        self.current_direction = random.choice([Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT])
        self.steps_in_same_direction = 0
        self.max_steps_same_dir = 4

        # Contadores
        self.step_count = 0
        self.food_collected = 0
        self.successful_returns = 0

    # ---------------------------------------------------
    # SENSORES E ATUALIZAÇÃO
    # ---------------------------------------------------
    def _update_sensor(self):
        """Atualiza sensores"""
        self.curr_observations.clear()

        obs = self._sensor.get_info(self)
        self.state.update_sensor_data(True, obs)
        self.step_count += 1

        if obs.surroundings:
            self.curr_observations[ObservationType.SURROUNDINGS] = obs.surroundings
            self._process_surroundings(obs.surroundings.payload.cells)

        if obs.location:
            self.curr_observations[ObservationType.LOCATION] = obs.location
            tile = getattr(obs.location.payload, 'tile_name', "").upper()

            if tile == "NEST":
                self.known_nest_position = self._position
                self.my_estimated_position = self._position
                self.has_seen_nest = True

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
        """Calcula a posição do ninho"""
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
        self.has_seen_nest = True

    def observation(self, obs: Observation):
        """Processa observações"""
        if obs.type == ObservationType.ACCEPTED:
            self.last_extrinsic_reward = obs.payload.reward

            if self.last_attempted_action:
                if self.last_attempted_action.name == "move":
                    direction = self.last_attempted_action.params.get("direction")
                    if direction:
                        # Atualiza posição REAL
                        self._position = self._position + direction

                        # Atualiza posição estimada
                        if direction == Direction.UP:
                            self.my_estimated_position = Position(self.my_estimated_position.x, self.my_estimated_position.y - 1)
                        elif direction == Direction.DOWN:
                            self.my_estimated_position = Position(self.my_estimated_position.x, self.my_estimated_position.y + 1)
                        elif direction == Direction.LEFT:
                            self.my_estimated_position = Position(self.my_estimated_position.x - 1, self.my_estimated_position.y)
                        elif direction == Direction.RIGHT:
                            self.my_estimated_position = Position(self.my_estimated_position.x + 1, self.my_estimated_position.y)

                        # Histórico
                        self.pos_history.append(self._position)
                        self.action_history.append(str(direction))

                        if self.stuck_counter > 0:
                            self.stuck_counter = 0

                    # Auto-Pickup Detection
                    if obs.payload.reward >= 40.0:
                        if not self.carrying:
                            self.carrying = True
                            self.food_collected += 1
                            log().print(f"[{self.name}] ✅ Pegou comida! Total: {self.food_collected}")
                        else:
                            self.carrying = False
                            self.successful_returns += 1
                            log().print(f"[{self.name}] 🎉 Depositou no ninho! Retornos: {self.successful_returns}")

                elif self.last_attempted_action.name == "pick":
                    self.carrying = True
                elif self.last_attempted_action.name == "drop":
                    self.carrying = False

        elif obs.type == ObservationType.DENIED:
            self.stuck_counter += 1

    # ---------------------------------------------------
    # LÓGICA DE DECISÃO - POLÍTICA FIXA
    # ---------------------------------------------------
    def act(self) -> Action:
        """Lógica principal - Política FIXA"""

        # 1. ATUALIZA SENSORES
        self._update_sensor()

        # 2. PRIORIDADE: Se está em cima de comida, APANHA!
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

        # 3. FILTRO DE PAREDES
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
            log().print(f"[{self.name}] ⚠️ Sem movimentos válidos! Esperando...")
            act = self.action.wait()
            self.last_attempted_action = act
            return act

        # 4. DETECÇÃO DE LOOP
        if self._is_stuck_in_loop() or self.stuck_counter > 3:
            log().print(f"[{self.name}] 🚨 LOOP DETECTADO! Modo pânico ativado")
            self.panic_mode = 5
            self.stuck_counter = 0

        # 5. MODO PÂNICO
        if self.panic_mode > 0:
            self.panic_mode -= 1
            final_dir = random.choice(valid_moves)

        # 6. MODO CARRYING (VOLTA AO NINHO)
        elif self.carrying:
            # Verifica se sensor diz que ninho está ao lado
            nest_direction = None
            if obs_surr:
                for direction, content in obs_surr.payload.cells.items():
                    content_upper = str(content).upper().strip()
                    if content_upper in ["NEST", "N"] and direction in valid_moves:
                        nest_direction = direction
                        break

            if nest_direction:
                final_dir = nest_direction
            else:
                # Navegação por coordenadas
                best_dir = self._calculate_best_direction(valid_moves)

                if best_dir:
                    final_dir = best_dir
                else:
                    # Fallback: movimento aleatório mas inteligente
                    if self.known_nest_position:
                        dx = self.known_nest_position.x - self.my_estimated_position.x
                        dy = self.known_nest_position.y - self.my_estimated_position.y

                        preferred_dirs = []
                        if dx > 0 and Direction.RIGHT in valid_moves: preferred_dirs.append(Direction.RIGHT)
                        elif dx < 0 and Direction.LEFT in valid_moves: preferred_dirs.append(Direction.LEFT)
                        if dy > 0 and Direction.DOWN in valid_moves: preferred_dirs.append(Direction.DOWN)
                        elif dy < 0 and Direction.UP in valid_moves: preferred_dirs.append(Direction.UP)

                        if preferred_dirs:
                            final_dir = random.choice(preferred_dirs)
                        else:
                            final_dir = random.choice(valid_moves)
                    else:
                        final_dir = random.choice(valid_moves)

        # 7. MODO EXPLORAÇÃO - POLÍTICA FIXA
        else:
            final_dir = self._explore_with_fixed_policy(valid_moves, obs_surr)

        # VERIFICAÇÃO FINAL DE SEGURANÇA
        if final_dir not in valid_moves:
            final_dir = random.choice(valid_moves)

        # Cria ação
        act = self.action.move(final_dir)
        self.last_attempted_action = act
        return act

    def _calculate_best_direction(self, valid_moves: list):
        """Calcula melhor direção para o ninho"""
        if not self.known_nest_position or not valid_moves:
            return None

        dx = self.known_nest_position.x - self.my_estimated_position.x
        dy = self.known_nest_position.y - self.my_estimated_position.y

        # Prioriza eixo com maior distância
        if abs(dx) > abs(dy):
            if dx > 0 and Direction.RIGHT in valid_moves: return Direction.RIGHT
            elif dx < 0 and Direction.LEFT in valid_moves: return Direction.LEFT
        else:
            if dy > 0 and Direction.DOWN in valid_moves: return Direction.DOWN
            elif dy < 0 and Direction.UP in valid_moves: return Direction.UP

        # Fallback
        if abs(dx) > abs(dy):
            if dy > 0 and Direction.DOWN in valid_moves: return Direction.DOWN
            elif dy < 0 and Direction.UP in valid_moves: return Direction.UP
        else:
            if dx > 0 and Direction.RIGHT in valid_moves: return Direction.RIGHT
            elif dx < 0 and Direction.LEFT in valid_moves: return Direction.LEFT

        return None

    def _explore_with_fixed_policy(self, valid_moves: list, obs_surr) -> Direction:
        """Exploração com política FIXA"""
        # 1. PRIORIDADE: Se vê comida, vai buscar!
        if obs_surr:
            cells = obs_surr.payload.cells
            for direction, content in cells.items():
                if direction == Direction.NONE: continue
                content_upper = str(content).upper().strip()
                if content_upper in ["FOOD", "F", "RESOURCE"] and direction in valid_moves:
                    return direction

        # 2. Inércia: mantém direção se possível
        if self.current_direction in valid_moves:
            self.steps_in_same_direction += 1

            # Muda de direção após muitos passos na mesma
            if self.steps_in_same_direction >= self.max_steps_same_dir:
                if self.current_direction in [Direction.UP, Direction.DOWN]:
                    perpendicular = [Direction.LEFT, Direction.RIGHT]
                else:
                    perpendicular = [Direction.UP, Direction.DOWN]

                available = [d for d in perpendicular if d in valid_moves]
                if available:
                    new_dir = random.choice(available)
                    self.current_direction = new_dir
                    self.steps_in_same_direction = 1
                    return new_dir

            return self.current_direction

        # 3. Se direção atual não é válida, escolhe nova
        new_direction = random.choice(valid_moves)
        self.current_direction = new_direction
        self.steps_in_same_direction = 1
        return new_direction

    def _is_stuck_in_loop(self) -> bool:
        """Detecta loops"""
        if len(self.pos_history) < 6: return False
        recent = list(self.pos_history)[-6:]
        return len(set(recent)) <= 2