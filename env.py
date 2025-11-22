from abstract.agent import Agent

from component.action import Action
from component.observation import Observation
from map.map import Map


class Environment:

    size = 0
    agents = []

    def __init__(self, problem: str, size, agents:list[Agent]):
        self.problem = problem
        self.agents = agents
        self.size = size
        self.map = Map(self)

    def send_observation(self, agent: Agent) -> Observation:
        pass

    def update(self):
        pass

    def act(self, action: Action, agent: Agent):
        pass

    def render(self):
        pass