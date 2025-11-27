from enum import Enum

class Direction(Enum):
    UP = (0,-1)
    DOWN = (0,1)
    LEFT = (-1,0)
    RIGHT = (1,0)
    NONE = (0,0)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<{self.name}>"