from enum import Enum

class REWARD(float, Enum):
    NONE = 0.0
    MOVED = -0.5
    MOVED_CLOSER = 1.0
    BUMP_AGENT = -0.5
    BUMP_COLLIDEABLE = -4.5
    OUT_OF_BOUNDS = -5.5
    STAND_STILL = -2.0
    DENY_PICK = -0.1
    REACH_OBJECTIVE = 100.0