import random
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from core.logger import log
from map.position import Position


class Ferb(Navigator2D):
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)

        self.problem = problem
        self._position = Position(*properties.get("starting_position", (0, 0)))
        self.char = properties.get("char", "F")

        # Estado
        self.carrying = False
        self.last_attempted_action = None

        # Sistema anti-loop para foraging
        self.pos_history = []
        self.stuck_counter = 0
        self.panic_mode = 0

        # Sistema de direção aleatória
        self.random_walk = True  # Sempre caminhada aleatória quando não tem comida
        self.wander_tendency = 0.8  # 80% chance de continuar na mesma direção

        log().print(f"{name}: Inicializado para {problem} (comportamento aleatório)")

    # ---------------------------------------------------
    # OBSERVAÇÃO
    # ---------------------------------------------------
    def observation(self, obs: Observation):
        if obs.type == ObservationType.ACCEPTED:
            # Deteção via Reward (Auto-Pickup)
            if obs.payload.reward >= 40.0:
                if self.problem == "foraging":
                    if not self.carrying:
                        self.carrying = True
                    else:
                        self.carrying = False

            # Atualiza posição quando movimento é aceito
            if self.last_attempted_action and self.last_attempted_action.name == "move":
                direction = self.last_attempted_action.params.get("direction")
                if direction:
                    self._position = self._position + direction
                    # Guarda histórico de posições
                    self.pos_history.append(self._position)
                    if len(self.pos_history) > 10:
                        self.pos_history.pop(0)
                    # Reseta contador de stuck se se moveu
                    self.stuck_counter = 0

        elif obs.type == ObservationType.DENIED:
            self.stuck_counter += 1

    # ---------------------------------------------------
    # MÉTODOS AUXILIARES PARA FORAGING
    # ---------------------------------------------------
    def _get_valid_moves(self) -> list:
        """Obtém movimentos válidos (não paredes)"""
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

        return valid_moves

    def _is_stuck(self) -> bool: #ta preso ou em loop
        if self.stuck_counter >= 3:
            return True

        if len(self.pos_history) >= 6:
            # Verifica se está repetindo as últimas posições
            recent = self.pos_history[-6:]
            if len(set(recent)) <= 2:
                return True

        return False

    def _scan_for_food(self, valid_moves: list) -> Direction: #verifica comida redondezas
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        if obs_surr:
            for direction, content in obs_surr.payload.cells.items():
                if direction not in valid_moves:
                    continue

                content_upper = str(content).upper().strip()
                if content_upper in ["FOOD", "F", "RESOURCE"]: #viu comida
                    return direction
        return None

    def _scan_for_nest(self, valid_moves: list) -> Direction:
        """Verifica se vê ninho nas redondezas (quando carregando)"""
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        if obs_surr:
            for direction, content in obs_surr.payload.cells.items():
                if direction not in valid_moves:
                    continue

                content_upper = str(content).upper().strip()
                if content_upper in ["NEST", "N"]: #viu ninho
                    return direction
        return None

    def _choose_random_direction(self, valid_moves: list, avoid_recent: bool = True) -> Direction:
        #random diretion
        if not valid_moves:
            return None

        # Se temos histórico de ações recentes, evita voltar para trás imediatamente
        if avoid_recent and self.last_attempted_action and len(valid_moves) > 1:
            if self.last_attempted_action.name == "move":
                last_dir = self.last_attempted_action.params.get("direction")
                if last_dir:
                    opposite = last_dir.opposite() if hasattr(last_dir, 'opposite') else None
                    # Remove direção oposta das opções (evita ir e voltar)
                    filtered = [d for d in valid_moves if d != opposite]
                    if filtered:
                        return random.choice(filtered)

        # Escolha totalmente aleatória
        return random.choice(valid_moves)

    def _navigate_randomly_with_momentum(self, valid_moves: list) -> Direction:
        #Caminha aleatoriamente com inercia
        if not valid_moves:
            return None
        # Se o último movimento foi aceito e ainda é válido, tem chance de continuar
        if (self.last_attempted_action and
                self.last_attempted_action.name == "move" and
                random.random() < self.wander_tendency):

            last_dir = self.last_attempted_action.params.get("direction")
            if last_dir and last_dir in valid_moves:
                return last_dir

        # Caso contrário, escolhe aleatoriamente
        return self._choose_random_direction(valid_moves)

    # ---------------------------------------------------
    # ACT - COMPORTAMENTO ALEATÓRIO PARA FORAGING
    # ---------------------------------------------------
    def act(self) -> Action:
        # Atualiza sensores
        if not self.has_observations():
            obs = self._sensor.get_info(self)
            self.state.update_sensor_data(True, obs)
            if obs.surroundings:
                self.curr_observations[ObservationType.SURROUNDINGS] = obs.surroundings
            if obs.location:
                self.curr_observations[ObservationType.LOCATION] = obs.location

        # Acao direta primeiro caso esteja em cima de um recurso
        obs_loc = self.curr_observations.get(ObservationType.LOCATION)
        if obs_loc:
            tile = getattr(obs_loc.payload, 'tile_name', "").upper()

            # Foraging: Se está em cima de comida E e n tem food - apanha
            if self.problem == "foraging":
                if not self.carrying and tile in ["FOOD", "RESOURCE", "F"]:
                    act = self.action.pick()
                    self.last_attempted_action = act #apanhar food
                    return act

                # Se está no ninho E está carregando
                if self.carrying and tile == "NEST":
                    act = self.action.drop()
                    self.last_attempted_action = act #entregar
                    return act

        valid_moves = self._get_valid_moves() #obter valid moves

        if not valid_moves: # caso nao hajam movimentos validos espera
            act = self.action.wait()
            self.last_attempted_action = act
            return act

        #detecao de stuck
        if self._is_stuck() or self.panic_mode > 0:
            if self.panic_mode == 0:
                self.panic_mode = 3 #3 movs fica em panico
            else:
                self.panic_mode -= 1
            # No modo pânico, movimento totalmente aleatório
            final_dir = self._choose_random_direction(valid_moves, avoid_recent=False)

            act = self.action.move(final_dir)
            self.last_attempted_action = act
            return act

        # ====================================================================
        # Lógica por problema

        if self.problem == "foraging":
            # FORAGING: COMPORTAMENTO ALEATÓRIO
            if self.carrying: #se tiver a carregar
                # Primeiro verifica se vê ninho diretamente
                nest_dir = self._scan_for_nest(valid_moves)
                if nest_dir:
                    final_dir = nest_dir
                else:
                    # Se não vê ninho, movimento aleatório
                    final_dir = self._choose_random_direction(valid_moves)
            # Se não está carregando, comportamento de busca aleatória
            else:
                # Verifica se vê comida nas redondezas
                food_dir = self._scan_for_food(valid_moves)
                if food_dir:
                    final_dir = food_dir #vai em direcao a comida
                else:
                    # COMPORTAMENTO ALEATÓRIO TOTAL
                    final_dir = self._navigate_randomly_with_momentum(valid_moves)
                    log().vprint(f"{self.name}: Exploração aleatória: {final_dir}")

        elif self.problem == "lighthouse":
            obs_dir = self.curr_observations.get(ObservationType.DIRECTION)
            if obs_dir:
                dx, dy = obs_dir.payload.direction
                candidates = []
                if dx in valid_moves:
                    candidates.append(dx)
                if dy in valid_moves:
                    candidates.append(dy)
                if candidates:
                    final_dir = random.choice(candidates)
                    #seguir direcao farol

            if not final_dir:
                final_dir = self._choose_random_direction(valid_moves)

        else:
            #caso oturos problemas - movimento aleatório
            final_dir = self._choose_random_direction(valid_moves)

        #final seg
        if final_dir not in valid_moves:
            log().vprint(f"⚠️ {self.name}: Direção inválida, corrigindo...")
            final_dir = self._choose_random_direction(valid_moves)

        #Cria ação
        act = self.action.move(final_dir)
        self.last_attempted_action = act
        return act