import json
from typing import Union

from abstract import Agent
from map.entity import MapEntity, EntityPosition, AgentData
from map.position import Position

_EMPTY_CELL = " ."
OUT_OF_BOUNDS = Position(-1,-1)


def _format_char(char: str):
    return f" {char[:2]:>2}"


class Map:
    _char_entity_mapping: dict[str, MapEntity]
    _boundaries: Position
    _map_cells: dict[Position, MapEntity]

    def __init__(self, problem: str, data: dict, env):
        self._env = env

        self._char_entity_mapping = self._load_obst_schema("map/entity_schema.ndjson")
        self._load_map_settings(data)
        self._map_cells = self._load_map_grid("problem/" + problem + "/" + data["file"] + ".grid")

        self._max_x, self._max_y = self._boundaries.get()

    @staticmethod
    def _load_obst_schema(path: str) -> dict[str, MapEntity]:
        _char_to_ent = {}
        with open(path, "r") as f:
            for line in f:
                data = json.loads(line)
                obj = MapEntity(**data)
                _char_to_ent[obj.char] = obj
        return _char_to_ent

    def _load_map_settings(self, data:dict) -> None:
        (x, y) = data["boundaries"]
        self._boundaries = Position(x, y)

    def _load_map_grid(self, path: str) -> dict[Position, MapEntity]:
        (max_x, max_y) = self._boundaries.get()

        map_cells: dict[Position, MapEntity] = \
            {
                OUT_OF_BOUNDS: MapEntity("\0", "Boundarie", -9999.0, False, False, False, True)
            }

        with open(path, "r") as f:
            for y, line in enumerate(f):
                if y >= max_y:
                    break

                line = line.rstrip("\n")
                for x, ch in enumerate(line):
                    if x >= max_x:  # stop if beyond X boundary
                        break

                    if ch in self._char_entity_mapping:
                        map_cells[Position(x, y)] = self._char_entity_mapping[ch]  # will map the position to a entity TEMPLATE, reducing the memory

        return map_cells

    def _is_inbounds(self, pos: Position) -> bool:
        if not pos.is_strictly_less_than(self._boundaries):
            return False

        if pos.has_negative_coord():
            return False

        return True

    def get_position_data(self, pos: Position) -> Union[MapEntity, None]:
        if not self._is_inbounds(pos):
            return  self._map_cells[OUT_OF_BOUNDS]

        if self._map_cells.get(pos):
            return self._map_cells.get(pos)

        return None

    def get_entity_by_name(self, ent: str):
        results = {}
        for key, data in self._map_cells.items():
            if data.name.upper() == ent:
                results[key] = data

        return results

    def render(self, agent_positions: dict[Position, str]):

        if self._env.renderer != None:
            self._env.renderer.clear()

        for y in range(self._max_y):
            row = ""
            for x in range(self._max_x):

                pos = Position(x, y)

                if agent_positions.get(pos):
                    row += _format_char(agent_positions.get(pos))
                    continue

                if not self._map_cells.get(pos) or self._map_cells.get(pos).draw == False:
                    row += _format_char(_EMPTY_CELL)
                else:
                    row += _format_char(self._map_cells.get(pos).char)

            if self._env.renderer == None:
                print(row)
            else:
                self._env.renderer.buffer(row)

        print("") if self._env.renderer == None else self._env.renderer.draw()

