from enum import Enum

class REWARD(float, Enum):
    NONE = 0.0
    OUT_OF_BOUNDS = -1.5
    BUMP_COLLIDEABLE = -1.0
    BUMP_AGENT = -0.2
    STAND_STILL = -2.0
    MOVED = -0.5
    MOVED_CLOSER = 3.0
    REACH_OBJECTIVE = 100.0
    DENY_PICK = -0.1
