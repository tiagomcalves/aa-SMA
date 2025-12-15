from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from abstract.agent import Agent

@dataclass
class Action:
    name: str
    agent: "Agent"
    params: Dict[str, Any]

    def __post_init__(self):
        #print(f"created action {self.name} by {self.agent} with params {self.params}")
        #self.agent.state.update_action_taken(self)
        pass

class ActionResponse(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return count  # count starts at 0

    ACCEPTED = auto()
    DENIED = auto()
    HOLD = auto()