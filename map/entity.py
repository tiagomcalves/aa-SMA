from dataclasses import dataclass
from map.position import Position

@dataclass(frozen=True)
class MapEntity:
    char: str
    name: str
    reward: float
    remove_on_touch: bool
    custom: bool
    draw: bool


class EntityPosition:

    _step_count : int

    def __init__(self, pos: Position, entity: MapEntity):
        self.pos = pos
        self.obstacle = entity


    def stepped_on(self):
        self._step_count += 1

    def get_steps(self) -> int:
        return self._step_count