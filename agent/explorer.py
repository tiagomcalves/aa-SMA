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


    #def move(self, direction: Direction) -> None:
    #    vx, vy = direction.value
    #    self.position.move(vx, vy)

    def use_sensor(self) -> None:
        self.curr_observation = self._sensor.get_surroundings(self.get_position())

    def observation(self, obs: Observation):
        self.curr_observation = obs

        if obs.type == ObservationType.SURROUNDINGS:
            print(f"{self.name} checks its surroundings and is astounded")
            log.print(obs.payload)

    def act(self) -> Action:
        if self.has_observation():
            pass
        else:
            self.use_sensor()

        return Action.wait()
