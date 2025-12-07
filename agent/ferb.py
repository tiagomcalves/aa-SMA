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
        self._position = Position(*properties["starting_position"])
        self.char = properties["char"]
        self.temp_mem_moves = []  # Memória de curto prazo para não andar aos círculos
        self.last_move = Direction.NONE
        self.carrying = False
        self.last_attempted_action = None

    def observation(self, obs: Observation):
        if obs.type == ObservationType.ACCEPTED:
            # Atualiza estado de carga
            if self.last_attempted_action:
                if self.last_attempted_action.name == "pick":
                    self.carrying = True
                elif self.last_attempted_action.name == "drop":
                    self.carrying = False

            # Adiciona o movimento oposto à memória para evitar voltar para trás imediatamente
            if self.last_move != Direction.NONE:
                self.temp_mem_moves.append(self.last_move.opposite())
                # Mantém a memória curta (últimos 4 movimentos)
                if len(self.temp_mem_moves) > 4:
                    self.temp_mem_moves.pop(0)

        elif obs.type == ObservationType.DENIED:
            # Se bateu, limpa a memória para tentar outros caminhos
            self.temp_mem_moves.clear()

    def act(self) -> Action:
        if not self.has_observations():
            # Força update dos sensores se não tiver dados
            obs = self._sensor.get_info(self)
            self.state.update_sensor_data(True, obs)
            self.curr_observations[ObservationType.SURROUNDINGS] = obs.surroundings
            self.curr_observations[ObservationType.LOCATION] = obs.location

        # 1. INSTINTO (Prioridade Máxima)
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

        # 2. MOVIMENTO
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        valid_moves = []

        if obs_surr:
            # Filtra paredes e obstáculos
            valid_moves = [
                d for d, c in obs_surr.payload.cells.items()
                if c not in ["WALL", "OBSTACLE", "Wall", "Obstacle"] and d != Direction.NONE
            ]
        else:
            # Fallback se sensor falhar
            valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        if not valid_moves:
            return self.action.wait()

        good_opts = [d for d in valid_moves if d not in self.temp_mem_moves]

        final_move = None
        if good_opts:
            final_move = random.choice(good_opts)
        else:
            final_move = random.choice(valid_moves)

        self.last_move = final_move
        act = self.action.move(final_move)
        self.last_attempted_action = act
        return act