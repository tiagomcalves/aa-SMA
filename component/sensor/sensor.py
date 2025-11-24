from component.observation import Observation
from component.sensor.request import Surroundings
from map.position import Position


class Sensor:

    def __init__(self, env):
        self.env = env

    def get_info(self):
        pass

    def get_surroundings(self, pos: Position) -> Observation:
        request = Surroundings(pos)
        return self.env.handle_request(request.to_dict())


