from component.sensor.request import Surroundings
from map.position import Position


class Sensor:

    def __init__(self, env):
        self.env = env

    def get_info(self):
        pass

    def get_surroundings(self, pos: Position) -> None:
        request = Surroundings(pos)
        print(self.env.handle_request(request.to_dict()))

