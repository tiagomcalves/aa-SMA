from enum import Enum
from dataclasses import dataclass
from typing import Optional
from component.direction import Direction


class ObservationType(Enum):
    ACCEPTED_MOVE = "accepted_move"
    DIRECTION = "directions"
    SURROUNDINGS = "surroundings"
    STATUS = "status"
    LOCATION = "location"
    DENIED = "denied"
    ACCEPTED = "accepted"
    TERMINATE = "terminate"

class Observation:
    def __init__(self, o_type: ObservationType, payload: dict | None = None):
        payload_class = OBSERVATION_PAYLOADS.get(o_type)
        if payload_class:
            self.payload = payload_class(**(payload or {}))
        else:
            self.payload = None
        self.type = o_type


@dataclass
class SurroundingsPayload:
    cells: dict[Direction, str]

@dataclass
class StatusPayload:
    reward: float

@dataclass
class AcceptedMovePayload:
    direction: Direction

@dataclass
class AcceptedPayload:
    reward: float

@dataclass
class DeniedPayload:
    reward: float

@dataclass
class LocationPayload:
    distance: float

@dataclass
class GPSPayload:
    direction: tuple[Direction, Direction]

@dataclass
class EmptyPayload:
    pass

OBSERVATION_PAYLOADS = {
    ObservationType.SURROUNDINGS: SurroundingsPayload,
    ObservationType.STATUS: StatusPayload,
    ObservationType.LOCATION: LocationPayload,
    ObservationType.DIRECTION: GPSPayload,
    ObservationType.DENIED: EmptyPayload,
    ObservationType.ACCEPTED: EmptyPayload,
    ObservationType.ACCEPTED_MOVE: AcceptedMovePayload,
    ObservationType.TERMINATE: EmptyPayload,
}

@dataclass
class ObservationBundle:
    surroundings: Optional[Observation] = None
    directions: Optional[Observation] = None
    location: Optional[Observation] = None

    @classmethod
    def from_dict(cls, obs_dict: dict[str, Observation]):
        return cls(
            surroundings=obs_dict.get("surroundings"),
            directions=obs_dict.get("directions"),
            location=obs_dict.get("location"),
        )
