import json
from map.entity import MapEntity, EntityPosition
from map.position import Position

_EMPTY_CELL = " ."


def _format_char(char: str):
    return f" {char[:2]:>2}"


class Map:
    _char_entity_mapping: dict[str, MapEntity]
    _boundaries: Position
    _map_cells: dict[Position, MapEntity]

    def __init__(self, problem: str, env):
        self._env = env

        self._char_entity_mapping = self._load_obst_schema("map/entity_schema.ndjson")
        self._load_map_settings("problem/" + problem + "/map.json")
        self._map_cells = self._load_map_grid("problem/" + problem + "/map.grid")

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

    def _load_map_settings(self, path: str) -> None:
        with open(path, "r") as f:
            data = json.load(f)

        (x, y) = (map(int, data["boundaries"].split(",")))  #splits and maps as int
        self._boundaries = Position(x, y)

    def _load_map_grid(self, path: str) -> dict[Position, MapEntity]:
        (max_x, max_y) = self._boundaries.get()

        map_cells: dict[Position, MapEntity] = {}

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
        if pos.is_strictly_less_than(self._boundaries):
            return True
        return False

    def sensorAPI(self, pos: Position):
        pass

    def render(self, agent_positions: dict[Position, str]):
        for y in range(self._max_y):
            row = ""
            for x in range(self._max_x):

                pos = Position(x, y)
                #print(f"[render] Position {pos}: {self._map_cells.get(pos)}")
                if not self._map_cells.get(pos) or self._map_cells.get(pos).draw == False:
                    if agent_positions.get(pos):
                        row += _format_char(agent_positions.get(pos))
                        continue
                    else:
                        row += _format_char(_EMPTY_CELL)
                else:
                    row += _format_char(self._map_cells.get(pos).char)

            print(row)
        print("\n")
