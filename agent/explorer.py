from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observe import Observe
from map.position import Position

class Explorer(Navigator2D):

    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)
        self._position = Position(*properties["starting_position"])
        self.char = properties["char"]

    #def move(self, direction: Direction) -> None:
    #    vx, vy = direction.value
    #    self.position.move(vx, vy)

    def observation(self, obs: Observe):
        pass
