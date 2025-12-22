from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Optional

from component.action import Action
from component.direction import Direction
from map.entity import TileType


class ObservationType(Enum):
    NONE = "none"
    DIRECTION = "directions"
    SURROUNDINGS = "surroundings"
    STATUS = "status"
    LOCATION = "location"
    DENIED = "denied"
    ACCEPTED = "accepted"
    TERMINATE = "terminate"
    RESPONSE = "response"


class Observation:
    def __init__(self, o_type: ObservationType, payload: dict | object | None = None):
        self.type = o_type
        payload_class = OBSERVATION_PAYLOADS.get(o_type)

        if payload is None:
            self.payload = None

        # 1. Se for Dicionário -> Converte para Dataclass
        elif isinstance(payload, dict):
            self.payload = payload_class(**payload) if payload_class else payload

        # 2. Se for a Dataclass correta -> Aceita
        elif payload_class is not None and isinstance(payload, payload_class):
            self.payload = payload

        # 3. NOVO: Se for um objeto genérico (do Sensor) -> Tenta converter para Dataclass
        elif hasattr(payload, "__dict__") and payload_class is not None:
            try:
                # Tenta desempacotar os atributos do objeto para a Dataclass
                self.payload = payload_class(**payload.__dict__)
            except TypeError:
                # Se os campos não baterem certo, guarda como está
                self.payload = payload
        else:
            # Fallback final ou Erro
            if payload_class:
                raise TypeError(
                    f"payload must be dict or {payload_class.__name__} instance, got {type(payload).__name__}")
            self.payload = payload

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

    @classmethod
    def response(cls, reward: float, moved: bool = False, payload: dict | ResponsePayload | None = None):
        if payload is not None:
            return cls(ObservationType.RESPONSE, payload)
        return cls(ObservationType.RESPONSE, {"reward": reward, "moved": moved})


@dataclass
class SurroundingsPayload:
    cells: dict[Direction, TileType]


@dataclass
class StatusPayload:
    reward: float


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
    tile: str


@dataclass
class GPSPayload:
    direction: tuple[Direction, Direction]


@dataclass
class EmptyPayload:
    pass


@dataclass
class ResponsePayload:
    reward: float
    moved: bool


OBSERVATION_PAYLOADS = {
    ObservationType.SURROUNDINGS: SurroundingsPayload,
    ObservationType.STATUS: StatusPayload,
    ObservationType.LOCATION: LocationPayload,
    ObservationType.DIRECTION: GPSPayload,
    ObservationType.DENIED: DeniedPayload,
    ObservationType.ACCEPTED: AcceptedPayload,
    ObservationType.TERMINATE: AcceptedPayload,
    ObservationType.RESPONSE: ResponsePayload,
}

DISABLED_SURROUNDINGS = Observation(ObservationType.SURROUNDINGS, SurroundingsPayload({Direction.UP: TileType.NONE, Direction.DOWN: TileType.NONE, Direction.LEFT: TileType.NONE, Direction.RIGHT: TileType.NONE}))
DISABLED_DIRECTIONS = Observation(ObservationType.DIRECTION, GPSPayload( (Direction.NONE, Direction.NONE)))
DISABLED_LOCATION = Observation(ObservationType.LOCATION, LocationPayload("N/A"))

@dataclass
class ObservationBundle:
    surroundings: Optional[Observation] = None
    directions: Optional[Observation] = None
    location: Optional[Observation] = None

    @classmethod
    def from_dict(cls, obs_dict: dict[str, Observation]):
        return cls(
            surroundings=obs_dict.get("surroundings", DISABLED_SURROUNDINGS),
            directions=obs_dict.get("directions", DISABLED_DIRECTIONS),
            location=obs_dict.get("location", DISABLED_LOCATION),
        )

    def unpack(self, obs_type: ObservationType) -> dict | object | None:
        if obs_type == ObservationType.SURROUNDINGS:
                return self.surroundings.payload.cells
        elif obs_type == ObservationType.DIRECTION:
                return self.directions.payload.direction
        elif obs_type == ObservationType.LOCATION:
                return self.location.payload.tile

        return None