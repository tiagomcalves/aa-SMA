from __future__ import annotations

class Position:

    _pos : tuple[int, int]

    def __init__(self, pos: tuple[int, int]):
        if pos[0] < 0 or pos[1] < 0:
            ValueError(f"Position cant have a coord below 0: {pos}")

        self._pos = pos

    def get(self) -> tuple[int,int]:
        return self.pos

    def set(self, x: int, y: int) -> None:
        self.pos = (x, y)

    def move(self, x, y):
        self.pos = (self.pos[0] + x, self.pos[1] + y)

    def is_strictly_less_than(self, other:Position):
        other_t = other.get()
        if self._pos[0] < other_t[0] and self._pos[1] < other_t[1]:
            return True
        return False
