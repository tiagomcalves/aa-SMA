from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Any

from component.direction import Direction

@dataclass
class Action:
    name: str
    params: Dict[str, Any]

    @classmethod
    def move(cls, vector: Direction):
        return cls("move", {"direction":vector})

    @classmethod
    def interact(cls, target_id: str ):
        return cls("interact", {"target": target_id})

    @classmethod
    def pick(cls):
        return cls("pick", {})

    @classmethod
    def drop(cls, item_id: str):
        return cls("drop", {"item": item_id})

    @classmethod
    def wait(cls):
        return cls("wait", {})


class ActionResponse(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return count  # count starts at 0

    ACCEPTED = auto()
    DENIED = auto()
    HOLD = auto()