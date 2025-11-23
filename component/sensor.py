from component.observation import Observation
from map.position import Position

class Sensor:

    def __init__(self, env):
        self.env = env

    def get_info(self):
        pass

    def get_surroundings(self, pos: Position) -> Observation:
        pass