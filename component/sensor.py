from abstract.agent import Agent
from env import Environment

class Sensor:

    def __init__(self, env: Environment, agent: Agent):
        self.agent = agent
        self.env = env

    def get_info(self):
