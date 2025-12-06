from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Optional

from pywin.mfc.object import Object

from component.action import Action
from component.direction import Direction


class ObservationType(Enum):
    NONE = "none"
    DIRECTION = "directions"
    SURROUNDINGS = "surroundings"
    STATUS = "status"
    LOCATION = "location"
    DENIED = "denied"
    ACCEPTED = "accepted"
    TERMINATE = "terminate"


class Observation:
    def __init__(self, o_type: ObservationType, payload: dict | object | None = None):
        self.type = o_type
        payload_class = OBSERVATION_PAYLOADS.get(o_type)

        if payload is None:
            self.payload = None
        elif isinstance(payload, dict):
            self.payload = payload_class(**payload) if payload_class else payload
        elif payload_class is not None and isinstance(payload, payload_class):
            self.payload = payload
        else:
            raise TypeError(f"payload must be dict or {payload_class} instance, got {type(payload)}")

    @classmethod
    def none(cls):
        return cls(ObservationType.NONE, None)

    @classmethod
    def denied(cls, action: Action = None, reward: float = None, payload: dict | DeniedPayload | None = None):
        if payload is not None:
            return cls(ObservationType.DENIED, payload)
        if action is None or reward is None:
            raise ValueError("action and reward are required when payload is not provided")
        return cls(ObservationType.DENIED, {"action": action, "reward": reward})

    @classmethod
    def accepted(cls, action: Action = None, reward: float = None, payload: dict | AcceptedPayload | None = None):
        if payload is not None:
            return cls(ObservationType.ACCEPTED, payload)
        if action is None or reward is None:
            raise ValueError("action and reward are required when payload is not provided")
        return cls(ObservationType.ACCEPTED, {"action": action, "reward": reward})

    @classmethod
    def terminate(cls, action: Action = None, reward: float = None, payload: dict | AcceptedPayload | None = None):
        if payload is not None:
            return cls(ObservationType.TERMINATE, payload)
        if action is None or reward is None:
            raise ValueError("action and reward are required when payload is not provided")
        return cls(ObservationType.TERMINATE, {"action": action, "reward": reward})

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
    action: Action
    reward: float

@dataclass
class DeniedPayload:
    action: Action
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
    ObservationType.DENIED: DeniedPayload,
    ObservationType.ACCEPTED: AcceptedPayload,
    ObservationType.TERMINATE: AcceptedPayload,
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

    def unpack(self, obs_type: ObservationType) -> dict|object|None:
        if obs_type == ObservationType.SURROUNDINGS and self.surroundings is not None:
            return self.surroundings.payload.cells
        elif obs_type == ObservationType.DIRECTION and self.directions is not None:
            return self.directions.payload.direction
        elif obs_type == ObservationType.LOCATION and self.location is not None:
            return self.location.payload.distance
        return None