from enum import Enum

class REWARD(float, Enum):
    NONE = 0.0
    OUT_OF_BOUNDS = -1.0
    BUMP_COLLIDEABLE = -0.5
    STAND_STILL = -1.0
    MOVED = 1.0
    REACH_OBJECTIVE = 100.0
