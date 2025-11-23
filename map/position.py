from __future__ import annotations

from numpy.ma.core import true_divide

from component.direction import Direction


class Position:

    _pos : tuple[int, int]

    def __init__(self, x: int, y: int):
        self._pos = (x,y)

    def __hash__(self):
        return hash(self._pos)

    def __eq__(self, other):
        _other = other.get()
        return self._pos[0] == _other[0] and self._pos[1] == _other[1]

    def __add__(self, other):
        if isinstance(other, Position):
            (ox, oy) = other.get()
        elif isinstance(other, Direction):
            (ox, oy) = other.value
        else:
            return NotImplemented

        return Position(self._pos[0] + ox, self._pos[1] + oy)

    def __radd__(self, other):
        return self.__add__(other)

    def get(self) -> tuple[int,int]:
        return self._pos

    def set(self, x: int, y: int) -> None:
        self._pos = (x, y)

    def move(self, x:int, y:int):
        self._pos = (self._pos[0] + x, self._pos[1] + y)

    def get_from_direction(self, direction:Direction) -> Position:
        return self + direction

    def is_strictly_less_than(self, other:Position) -> bool:
        other_t = other.get()
        if self._pos[0] < other_t[0] and self._pos[1] < other_t[1]:
            return True
        return False

    def has_negative_coord(self) -> bool:
        if self.get()[0] < 0 or self.get()[1] < 0:
            return True
        return False

    def __str__(self):
        return f"({self._pos[0]},{self._pos[1]})"


# Invalid position instance
Position.OUT_OF_BOUNDS = super(Position, Position).__new__(Position)
Position.OUT_OF_BOUNDS._pos = (-1, -1)