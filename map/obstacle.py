from dataclasses import dataclass
from map.position import Position

@dataclass(frozen=True)
class Obstacle:
    char: str
    name: str
    reward: float
    remove_on_touch: bool


class ObstaclePosition:

    _step_count : int

    def __init__(self, pos: Position, obstacle: Obstacle):
        self.pos = pos
        self.obstacle = obstacle


    def stepped_on(self):
        self._step_count += 1

    def get_steps(self) -> int:
        return self._step_count