from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observe import Observe
from map.position import Position

class Explorer(Navigator2D):

    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)
        starting_position = properties["starting_position"].split(",")
        self.position = Position( int(starting_position[0]), int(starting_position[1]) )
        self.char = properties["char"]

    def get_position(self) -> Position:
        return self.position

    #def move(self, direction: Direction) -> None:
    #    vx, vy = direction.value
    #    self.position.move(vx, vy)

    def observation(self, obs: Observe):
        pass

    def act(self) -> Action:
        pass