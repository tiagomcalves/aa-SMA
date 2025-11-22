import json
from map.obstacle import Obstacle
from map.position import Position


class Map:

    _obstacle_type : dict[str, Obstacle]
    _boundaries : Position

    def __init__(self, problem: str, env):
        self._env = env
        self._obstacle_type = {}
        self._load_obst_schema("map/obstacle_schema.ndjson")
        self._load_map_settings("problem/" + problem + "/map.json")
        #self._load_map_grid("problem/" + problem + "map.grid")

    def _load_obst_schema(self, path: str) -> None:
        with open(path, "r") as f:
            for line in f:
                data = json.loads(line)
                obj = Obstacle(**data)
                self._obstacle_type[obj.char] = obj

    def _load_map_settings(self, path: str) -> None:
        with open(path, "r") as f:
            data = json.load(f)

        (x, y) = (map(int, data["boundaries"].split(",") )) #splits and maps as int
        self._boundaries = Position( (x,y) )

    def is_inbounds(self, pos:Position) -> bool:
        if pos.is_strictly_less_than(self._boundaries):
            return True
        return False