from component.observe import Observe
from map.position import Position

class Sensor:

    def __init__(self, env):
        self.env = env

    def get_info(self):
        pass

    def get_surroundings(self, pos: Position) -> Observe:
        pass