from __future__ import annotations
from component.direction import Direction


class Position:
    # Constante estática inicializada no fundo do ficheiro
    OUT_OF_BOUNDS = None

    def __init__(self, x: int, y: int):
        self._pos = (x, y)

    @property
    def x(self):
        return self._pos[0]

    @property
    def y(self):
        return self._pos[1]

    def get(self) -> tuple[int, int]:
        return self._pos

    # --- O CORAÇÃO DO PROBLEMA (HASH e EQ) ---
    def __hash__(self):
        # Garante que Position(1,1) tem sempre o mesmo ID de hash
        return hash(self._pos)

    def __eq__(self, other):
        # Garante que Position(1,1) == Position(1,1)
        if isinstance(other, Position):
            return self._pos == other._pos
        if isinstance(other, tuple):
            return self._pos == other
        return False

    # ------------------------------------------

    def __add__(self, other):
        dx, dy = 0, 0
        if isinstance(other, Position):
            dx, dy = other.x, other.y
        elif isinstance(other, Direction):
            # Tenta obter valor do Enum, ou usa o próprio se for tuplo
            val = other.value if hasattr(other, 'value') else other
            dx, dy = val
        elif isinstance(other, tuple):
            dx, dy = other

        return Position(self.x + dx, self.y + dy)

    def is_strictly_less_than(self, other: Position) -> bool:
        return self.x < other.x and self.y < other.y

    def has_negative_coord(self) -> bool:
        return self.x < 0 or self.y < 0

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __repr__(self):
        return self.__str__()


# Inicialização segura
Position.OUT_OF_BOUNDS = Position(-1, -1)