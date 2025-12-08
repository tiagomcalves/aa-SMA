import random
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from map.position import Position


class Ferb(Navigator2D):

    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)
        self._position = Position(*properties["starting_position"])
        self.char = properties["char"]

        # Inércia
        self.current_direction = random.choice([Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT])
        self.carrying = False
        self.last_attempted_action = None

        # Heurística de Ninho (Canto Superior Esquerdo por defeito)
        self.nest_position = Position(1, 1)

    def observation(self, obs: Observation):
        if obs.type == ObservationType.ACCEPTED:
            # Auto-Pickup Detection
            if obs.payload.reward >= 40.0:
                self.carrying = not self.carrying  # Toggle se receber grande recompensa

            elif self.last_attempted_action:
                if self.last_attempted_action.name == "pick":
                    self.carrying = True
                elif self.last_attempted_action.name == "drop":
                    self.carrying = False

        elif obs.type == ObservationType.DENIED:
            # Se bateu (apesar do filtro), força mudança
            self.current_direction = Direction.NONE

    def act(self) -> Action:
        if not self.has_observations():
            obs = self._sensor.get_info(self)
            self.state.update_sensor_data(True, obs)
            self.curr_observations[ObservationType.SURROUNDINGS] = obs.surroundings
            self.curr_observations[ObservationType.LOCATION] = obs.location

        # 1. INSTINTO (Pick / Drop)
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

        # 2. FILTRO DE PAREDES (BARREIRA LÓGICA)
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)

        # Lista de tiles proibidos
        walls = ["WALL", "OBSTACLE", "Wall", "Obstacle", "#", "X"]

        # Só aceita direções que NÃO são paredes
        free_moves = []
        if obs_surr:
            for d, c in obs_surr.payload.cells.items():
                if d != Direction.NONE and c.upper() not in walls:
                    free_moves.append(d)
        else:
            # Fallback se sensor falhar (raro)
            free_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        # Se estiver encurralado, espera
        if not free_moves:
            return self.action.wait()

        # 3. VERIFICAÇÃO DE INÉRCIA
        # Se a direção atual bate numa parede (não está em free_moves), MUDA!
        if self.current_direction not in free_moves:
            self.current_direction = random.choice(free_moves)

        final_dir = self.current_direction

        # 4. MODO RETORNO (Se tiver carga, tenta ir para o Ninho)
        if self.carrying:
            best_dist = float('inf')
            best_move = None

            # Escolhe o melhor movimento APENAS da lista free_moves
            for move in free_moves:
                next_pos = self._position + move
                diff = self.nest_position - next_pos
                dist = (diff.x ** 2) + (diff.y ** 2)
                if dist < best_dist:
                    best_dist = dist
                    best_move = move

            if best_move:
                final_dir = best_move

        # Executa
        act = self.action.move(final_dir)
        self.last_attempted_action = act
        return act