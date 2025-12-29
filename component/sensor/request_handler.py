from abc import ABC, abstractmethod
from enum import Enum, auto

from core.logger import log
from component.sensor import registry
from component.direction import Direction
from component.observation import Observation, ObservationType
from map.entity import AgentData, TileType


# --- Classe Auxiliar para permitir acesso com ponto (obj.cells) ---
class Payload:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Handler(ABC):
    @abstractmethod
    def handle(self, agent_data: AgentData, env) -> Observation:
        pass


@registry.register_handler("location")
class LocationHandler(Handler):
    def handle(self, agent_data: AgentData, env) -> Observation:

        payload = Payload(tile=env.get_tile_as_str(agent_data.pos))
        return Observation(ObservationType.LOCATION, payload)


def return_tile_type( env, pos ):
    tile_data = env.get_tile_data(pos)

    if tile_data is None:
        return TileType.EMPTY

    elif tile_data.name.upper() == "BOUNDARIES":
        return TileType.BOUNDARIES

    elif tile_data.collideable:
        return TileType.COLLIDEABLE

    elif tile_data.name.upper() == "FOOD":
        return TileType.PICKABLE

    elif tile_data.name.upper() == "NEST":
        return TileType.NEST

    return -1


@registry.register_handler("surroundings")
class SurroundingsHandler(Handler):
    def handle(self, agent_data: AgentData, env) -> Observation:
        # APENAS as 4 direções cardinais
        surroundings_data = {}

        # Verifica UP
        pos = agent_data.pos + Direction.UP
        surroundings_data[Direction.UP] = return_tile_type(env, pos)

        # Verifica DOWN
        pos = agent_data.pos + Direction.DOWN
        surroundings_data[Direction.DOWN] = return_tile_type(env, pos)

        # Verifica LEFT
        pos = agent_data.pos + Direction.LEFT
        surroundings_data[Direction.LEFT] = return_tile_type(env, pos)

        # Verifica RIGHT
        pos = agent_data.pos + Direction.RIGHT
        surroundings_data[Direction.RIGHT] = return_tile_type(env, pos)

        payload = Payload(cells=surroundings_data)
        return Observation(ObservationType.SURROUNDINGS, payload)


@registry.register_handler("directions")
class DirectionsHandler(Handler):
    def handle(self, agent_data: AgentData, env) -> Observation:

        # --- LÓGICA NOVA (Smart Sensor) ---
        target_name = "OBJECTIVE"  # Default (Lighthouse)

        # Verifica se estamos num cenário de Recoleção (Foraging)
        if hasattr(agent_data, 'carrying'):
            if agent_data.carrying is None:
                # Mãos vazias: Procura Comida
                target_name = "FOOD"

                # Fallback: Se não houver comida, verifica se é o problema do Farol
                # Isto impede crashes se usares este sensor no problema do Farol
                if not env.get_entities_by_type(target_name):
                    if env.get_entities_by_type("OBJECTIVE"):
                        target_name = "OBJECTIVE"
            else:
                # Mãos cheias: Procura o Ninho para depositar
                target_name = "NEST"

        # Usa o metodo genérico que adicionámos ao Environment
        targets = env.get_entities_by_type(target_name)

        # Se não houver alvos (ex: comida acabou), retorna Direção Nula
        if targets is None or len(targets) == 0:
            payload = Payload(direction=(Direction.NONE, Direction.NONE))
            return Observation(ObservationType.DIRECTION, payload)

        # --- Lógica de Proximidade (Inalterada) ---
        shortest_distance_pos = None
        shortest_distance = None
        (px, py) = agent_data.pos.get()

        for pos, entity in targets.items():
            (ox, oy) = pos.get()
            dist = (ox - px) ** 2 + (oy - py) ** 2

            if shortest_distance is None or dist < shortest_distance:
                shortest_distance = dist
                shortest_distance_pos = pos

        (ox, oy) = shortest_distance_pos.get()
        x_direction = Direction.NONE
        y_direction = Direction.NONE

        if ox - px < 0:
            x_direction = Direction.LEFT
        elif ox - px > 0:
            x_direction = Direction.RIGHT

        if oy - py < 0:
            y_direction = Direction.UP
        elif oy - py > 0:
            y_direction = Direction.DOWN

        payload = Payload(direction=(x_direction, y_direction))
        return Observation(ObservationType.DIRECTION, payload)