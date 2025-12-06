import random

from abstract.agent import AgentStatus
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
        self.temp_mem_moves = []
        self.visited_positions = []
        self.last_move = Direction.NONE

    def observation(self, obs: Observation):
        if obs.type == ObservationType.NONE:
            self.use_sensor()
            return

        if obs.type == ObservationType.TERMINATE:
            self.status = AgentStatus.TERMINATED
            self.state.set_final_state()

        elif obs.type == ObservationType.DENIED:
            self.state.update_sensor_data()

        elif obs.type == ObservationType.ACCEPTED:
            self.curr_observations.clear()
            self.temp_mem_moves.clear()
            action = obs.payload
            # AcceptedPayload(action=Action(name='move', agent=<agent.ferb.Ferb object at 0x0000024E6B655F70>, params={'direction': <RIGHT>}), reward=1.0)
            reward = obs.payload.reward
            self.temp_mem_moves.append(self.last_move.opposite())

        self.state.log_state()

    def act(self) -> Action:
        if not self.has_observations():
            self.observation(Observation.none())

        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)

        if obs_surr and obs_surr.payload.cells[Direction.NONE] == "OBJECTIVE":
            return self.action.pick()

        mem_moves = self.temp_mem_moves  #reference, not a copy

        log().vprint(f"{self.name} saved moves: {[str(move) for move in mem_moves]}")

        obs_direc = self.curr_observations.get(ObservationType.DIRECTION)

        if obs_direc:
            x_direc, y_direc = obs_direc.payload.direction
            if x_direc not in mem_moves:
                mem_moves.append(x_direc)
                return self.action.move(x_direc)

            if y_direc not in mem_moves:
                mem_moves.append(y_direc)
                return self.action.move(y_direc)

        if obs_surr:

            while True:
                option = random.choice(list(obs_surr.payload.cells))
                if option not in mem_moves:
                    break

            mem_moves.append(option)
            return self.action.move(option)

        return self.action.wait()
