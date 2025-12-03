from enum import Enum

class Direction(Enum):
    UP = (0,-1)
    DOWN = (0,1)
    LEFT = (-1,0)
    RIGHT = (1,0)
    NONE = (0,0)

    def opposite(self):
        if self is Direction.UP:
            return Direction.DOWN
        if self is Direction.DOWN:
            return Direction.UP
        if self is Direction.LEFT:
            return Direction.RIGHT
        if self is Direction.RIGHT:
            return Direction.LEFT
        if self is Direction.NONE:
            return Direction.NONE
        return None

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<{self.name}>"