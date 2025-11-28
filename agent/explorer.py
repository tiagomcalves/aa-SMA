import random

from abstract.nav2d import Navigator2D
from component.action import Action
from component.observation import Observation, ObservationType
from core.logger import log
from map.position import Position


class Explorer(Navigator2D):

    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)
        self._position = Position(*properties["starting_position"])
        self.char = properties["char"]

    def use_sensor(self) -> Observation:
        return self._sensor.get_surroundings(self)

    def observation(self, obs: Observation):
        self.curr_observation = obs
        if obs.type == ObservationType.SURROUNDINGS:
            log().print(obs.payload)

    def act(self) -> Action:
        if not self.has_observation():
            self.use_sensor()
            # observation( use sensor? )
            return Action.wait(self)

        if self.curr_observation.type == ObservationType.SURROUNDINGS:
            options = self.curr_observation.payload.cells
            key = random.choice(list(options.keys()))
            return Action.move(self, key)

        return Action.wait()
