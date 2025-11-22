from abstract.agent import Agent

from component.action import Action
from component.observation import Observation
from map.map import Map


class Environment:

    def __init__(self, problem: str):
        self.problem = problem
        self._map = Map(problem, self)

    def send_observation(self, agent: Agent) -> Observation:
        pass

    def update(self):
        pass

    def act(self, action: Action, agent: Agent):
        pass

    def render(self):
        pass