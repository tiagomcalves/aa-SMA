from enum import Enum
from dataclasses import dataclass
from component.direction import Direction
from core.logger import log


class ObservationType(Enum):
    DIRECTION = "directions"
    SURROUNDINGS = "surroundings"
    STATUS = "status"
    LOCATION = "location"

class Observation:
    def __init__(self, o_type: ObservationType, payload: dict):
        payload_class = OBSERVATION_PAYLOADS[o_type]
        self.payload = payload_class(**payload)
        self.type = o_type


@dataclass
class SurroundingsPayload:
    cells: dict[Direction, str]

@dataclass
class StatusPayload:
    reward: float

@dataclass
class LocationPayload:
    distance: float

@dataclass
class GPSPayload:
    direction: tuple[Direction, Direction]



OBSERVATION_PAYLOADS = {
    ObservationType.SURROUNDINGS: SurroundingsPayload,
    ObservationType.STATUS: StatusPayload,
    ObservationType.LOCATION: LocationPayload,
    ObservationType.DIRECTION: GPSPayload,
}
