from abstract.agent import Agent
from component.action import Action
from component.observe import Observe
from map.map import Map
from map.position import Position


class Environment:

    def __init__(self, problem: str):
        self.problem = problem
        self._map = Map(problem, self)

    def send_observation(self, agent: Agent) -> Observe:
        pass

    def update(self):
        pass

    def act(self, action: Action, agent: Agent):
        pass

    def render(self, agent_positions: dict[Position, str]):
        self._map.render(agent_positions)

    def retrieve_surroundings(self, pos:Position) -> Observe:
        pass
