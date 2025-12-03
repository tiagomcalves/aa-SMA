from component.observation import Observation, ObservationBundle
from component.sensor.request import Surroundings
from map.position import Position


class Sensor:

    def __init__(self, env):
        self.env = env

    def get_info(self, agent) -> ObservationBundle:
        raw = self.env.serve_data(agent)
        return ObservationBundle.from_dict(raw)

    def get_surroundings(self, agent) -> Observation:
        return self.env.serve_data(agent)["surroundings"]

    def get_direction(self, agent) -> Observation:
        return self.env.serve_data(agent)["directions"]


