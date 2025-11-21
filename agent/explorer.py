from abstract import Agent, Direction

class Explorer(Agent):

    position : (int, int)

    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)
        starting_position = properties["starting_position"].split(",")
        self.position = ( int(starting_position[0]), int(starting_position[1]) )

    def get_position(self) -> (int, int):
        return self.position

    def move(self, direction: Direction) -> None:
        vx, vy = direction.value
        self.position = (self.position[0] + vx, self.position[1] + vy)

