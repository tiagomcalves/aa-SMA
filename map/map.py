import json
import copy
from typing import Union, Optional

from map.entity import MapEntity, BOUNDARIES_TILE
from map.position import Position

_EMPTY_CELL = " ."


def _format_char(char: str):
    return f" {char[:2]:>2}"


class Map:
    _char_entity_mapping: dict[str, MapEntity]
    _boundaries: Position
    _map_cells: dict[Position, MapEntity]
    _boundaries_tile: MapEntity
    position_visits: dict[Position, int]

    def __init__(self, problem: str, data: dict, env):
        self._env = env

        self._boundaries_tile = BOUNDARIES_TILE

        self._char_entity_mapping = self._load_obst_schema("map/entity_schema.ndjson")
        self._load_map_settings(data)
        self._map_cells = self._load_map_grid("problem/" + problem + "/" + data["file"] + ".grid")
        self.position_visits = {}

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new

        new._env = None

        new._boundaries_tile = copy.deepcopy(self._boundaries_tile, memo)
        new._char_entity_mapping = copy.deepcopy(self._char_entity_mapping, memo)
        new._boundaries = copy.deepcopy(self._boundaries, memo)
        new._map_cells = copy.deepcopy(self._map_cells, memo)

        new._max_x = self._max_x
        new._max_y = self._max_y
        new.position_visits = {}

        return new

    @staticmethod
    def _load_obst_schema(path: str) -> dict[str, MapEntity]:
        _char_to_ent = {}
        try:
            with open(path, "r") as f:
                for line in f:
                    data = json.loads(line)
                    obj = MapEntity(**data)
                    _char_to_ent[obj.char] = obj
        except Exception as e:
            print(f"Error loading schema: {e}")
        return _char_to_ent

    def _load_map_settings(self, data: dict) -> None:
        (x, y) = data["boundaries"]
        self._boundaries = Position(x, y)
        self._max_x = x
        self._max_y = y

    def get_max_x(self):
        return self._max_x

    def get_max_y(self):
        return self._max_y

    def _load_map_grid(self, path: str) -> dict[Position, MapEntity]:
        map_cells: dict[Position, MapEntity] = {}

        try:
            with open(path, "r") as f:
                for y, line in enumerate(f):
                    if y >= self._max_y:
                        break

                    line = line.rstrip("\n")
                    for x, ch in enumerate(line):
                        if x >= self._max_x:
                            break

                        if ch in self._char_entity_mapping:
                            # Clona a entidade para garantir instâncias únicas se necessário
                            original = self._char_entity_mapping[ch]
                            map_cells[Position(x, y)] = copy.deepcopy(original)
        except FileNotFoundError:
            print(f"CRITICAL ERROR: Could not find map file at {path}")

        return map_cells

    def _is_inbounds(self, pos: Position) -> bool:
        if not pos.is_strictly_less_than(self._boundaries):
            return False
        if pos.has_negative_coord():
            return False
        return True

    def get_position_data(self, pos: Position) -> Optional[MapEntity]:
        """
        Retorna a entidade na posição ou None se fora do mapa.
        Se dentro e vazio, retorna _default_empty.
        """
        if not self._is_inbounds(pos):
            return self._boundaries_tile

        entity = self._map_cells.get(pos)
        if entity:
            return entity

        return None

    def get_entity_by_name(self, ent: str):
        results = {}
        target = ent.upper()
        for key, data in self._map_cells.items():
            if data.name.upper() == target:
                results[key] = data
        return results

    def find_ent_pos(self, ent: MapEntity):
        for pos, ent in self._map_cells.items():
            if ent.name.upper() == "OBJECTIVE":
                return pos
        return None

    def remove_entity(self, pos: Position):
        """ Remove fisicamente a entidade da grelha (ex: comida comida). """
        if pos in self._map_cells:
            del self._map_cells[pos]

    def add_entity(self, pos: Position, name: str):
        """ Cria e adiciona uma entidade numa posição específica (Respawn). """
        if not self._is_inbounds(pos):
            return

        # Procura o template da entidade no mapping original
        template = None
        for key, ent in self._char_entity_mapping.items():
            if ent.name.upper() == name.upper():
                template = ent
                break

        if template:
            # Insere uma cópia profunda na célula
            self._map_cells[pos] = copy.deepcopy(template)

    def add_count_to_position(self, pos: Position):
        self.position_visits[pos] = self.position_visits.get(pos, 0) + 1

    def render(self, agent_positions: dict[Position, str]):
        if self._env.renderer is not None:
            self._env.renderer.clear()

        for y in range(self._max_y):
            row = ""
            for x in range(self._max_x):
                pos = Position(x, y)

                # 1. Agente tem prioridade
                if pos in agent_positions:
                    char = agent_positions[pos]
                    row += _format_char(char)
                    continue

                # 2. Mapa estático (Comida, Paredes, etc)
                tile = self._map_cells.get(pos)

                if not tile or not tile.draw:
                    row += _format_char(_EMPTY_CELL)
                else:
                    row += _format_char(tile.char)

            if self._env.renderer is None:
                print(row)
            else:
                self._env.renderer.buffer(row)

        if self._env.renderer is not None:
            self._env.renderer.draw()