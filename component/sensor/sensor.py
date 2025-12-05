from component.observation import Observation, ObservationBundle

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


