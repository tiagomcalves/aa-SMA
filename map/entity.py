from dataclasses import dataclass
from enum import Enum, auto, IntEnum
from typing import Optional
from map.position import Position

class TileType(IntEnum):
    NONE = auto()
    EMPTY = auto()
    BOUNDARIES = auto()
    COLLIDEABLE = auto()
    COLLECTABLE = auto()
    NEST = auto()


@dataclass
class MapEntity:
    char: str
    name: str
    cost: float  # O erro dava-se aqui (falta de cost)
    collideable: bool
    active: bool  # Necessário pelo schema
    draw: bool

    # Mantivemos estes como opcionais (com default) caso o JSON não os tenha,
    # mas para o erro desaparecer, os de cima são os críticos.
    reward: float = 0.0
    remove_on_touch: bool = False
    custom: bool = False

    def __repr__(self):
        return f"{self.name} ({self.char})"


@dataclass
class AgentData:
    char: str
    name: str
    pos: Position
    score: float = 0.0

    # Adicionado para o problema de Foraging (Recoleção).
    # Se None = Mãos vazias. Se Float = Valor do recurso que carrega.
    carrying: Optional[float] = None


class EntityPosition:
    _step_count: int = 0

    def __init__(self, pos: Position, entity: MapEntity):
        self.pos = pos
        self.obstacle = entity
        self._step_count = 0

    def stepped_on(self):
        self._step_count += 1

    def get_steps(self) -> int:
        return self._step_count

BOUNDARIES_TILE = MapEntity(
            char=".", name="Boundaries", cost=0.0, collideable=True,
             active=True, draw=False
        )