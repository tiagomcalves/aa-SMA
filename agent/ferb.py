import random
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from map.position import Position


class Ferb(Navigator2D):
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)

        self.problem = problem  # Identifica o problema (Lighthouse vs Foraging)
        self._position = Position(*properties.get("starting_position", (0, 0)))
        self.char = properties.get("char", "F")

        # Estado
        self.carrying = False
        self.last_attempted_action = None

        # Inércia (para Foraging)
        self.current_direction = random.choice([Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT])

        # Conhecimento fixo (Heurística)
        self.nest_position = Position(1, 1)

    # ---------------------------------------------------
    # OBSERVAÇÃO & ATUALIZAÇÃO
    # ---------------------------------------------------
    def observation(self, obs: Observation):
        if obs.type == ObservationType.ACCEPTED:
            # Deteção de Auto-Pickup / Drop via Recompensa
            if obs.payload.reward >= 40.0:
                if self.problem == "foraging":
                    self.carrying = not self.carrying

            # Atualização manual se não houver auto-pickup
            elif self.last_attempted_action:
                if self.last_attempted_action.name == "pick":
                    if self.problem == "foraging": self.carrying = True
                elif self.last_attempted_action.name == "drop":
                    if self.problem == "foraging": self.carrying = False

        elif obs.type == ObservationType.DENIED:
            # Se bater, reseta a inércia para forçar nova decisão
            self.current_direction = Direction.NONE

    # ---------------------------------------------------
    # CÉREBRO (ACT)
    # ---------------------------------------------------
    def act(self) -> Action:
        if not self.has_observations():
            obs = self._sensor.get_info(self)
            self.state.update_sensor_data(True, obs)
            self.curr_observations[ObservationType.SURROUNDINGS] = obs.surroundings
            self.curr_observations[ObservationType.LOCATION] = obs.location
            self.curr_observations[ObservationType.DIRECTION] = obs.directions

        # 1. INSTINTOS (Prioridade Máxima: Se está em cima, age)
        obs_loc = self.curr_observations.get(ObservationType.LOCATION)
        if obs_loc:
            tile = getattr(obs_loc.payload, 'tile_name', "").upper()

            # Lighthouse: Ganhar o jogo
            if self.problem == "lighthouse" and tile in ["OBJECTIVE", "O", "@"]:
                act = self.action.pick();
                self.last_attempted_action = act;
                return act

            # Foraging: Apanhar/Largar
            if self.problem == "foraging":
                if not self.carrying and tile in ["FOOD", "RESOURCE"]:
                    act = self.action.pick();
                    self.last_attempted_action = act;
                    return act
                if self.carrying and tile == "NEST":
                    act = self.action.drop();
                    self.last_attempted_action = act;
                    return act

        # 2. FILTRO DE PAREDES (CRÍTICO: Nunca escolher parede)
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        bad_tiles = ["#", "WALL", "OBSTACLE", "X", "W"]

        valid_moves = []
        if obs_surr:
            for d, c in obs_surr.payload.cells.items():
                if d != Direction.NONE and str(c).upper().strip() not in bad_tiles:
                    valid_moves.append(d)
        else:
            valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        if not valid_moves:
            act = self.action.wait();
            self.last_attempted_action = act;
            return act

        final_dir = None

        # ====================================================================
        # LÓGICA ESPECÍFICA POR PROBLEMA
        # ====================================================================

        # --- CASO A: LIGHTHOUSE (Seguir Bússola) ---
        if self.problem == "lighthouse":
            obs_dir = self.curr_observations.get(ObservationType.DIRECTION)
            if obs_dir:
                dx, dy = obs_dir.payload.direction

                # Tenta seguir o sensor rigorosamente
                candidates = []
                if dx in valid_moves: candidates.append(dx)
                if dy in valid_moves: candidates.append(dy)

                if candidates:
                    final_dir = random.choice(candidates)

            # Se o sensor não ajudar (ou estiver bloqueado), Inércia
            if not final_dir:
                if self.current_direction in valid_moves:
                    final_dir = self.current_direction
                else:
                    final_dir = random.choice(valid_moves)
                    self.current_direction = final_dir

        # --- CASO B: FORAGING (Aspirador + Retorno) ---
        elif self.problem == "foraging":

            # B.1 Voltar a casa (Carrying)
            if self.carrying:
                # Navegação Euclidiana Simples para o Ninho (1,1)
                best_dist = float('inf')
                for move in valid_moves:
                    next_pos = self._position + move
                    diff = self.nest_position - next_pos
                    dist = (diff.x ** 2) + (diff.y ** 2)
                    if dist < best_dist:
                        best_dist = dist
                        final_dir = move

            # B.2 Explorar (Vazio) -> INÉRCIA COM MUDANÇA DE EIXO
            else:
                if self.current_direction in valid_moves:
                    final_dir = self.current_direction
                else:
                    # Bateu! Muda de eixo para não ficar preso em corredores
                    # Se estava na Vertical, tenta Horizontal e vice-versa
                    if self.current_direction in [Direction.UP, Direction.DOWN]:
                        options = [d for d in [Direction.LEFT, Direction.RIGHT] if d in valid_moves]
                    else:
                        options = [d for d in [Direction.UP, Direction.DOWN] if d in valid_moves]

                    if options:
                        final_dir = random.choice(options)
                    else:
                        final_dir = random.choice(valid_moves)  # O que der

                    self.current_direction = final_dir

        # ====================================================================

        # Fallback de segurança
        if not final_dir or final_dir not in valid_moves:
            final_dir = random.choice(valid_moves)

        act = self.action.move(final_dir)
        self.last_attempted_action = act
        return act