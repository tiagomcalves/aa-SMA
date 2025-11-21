from abstract.agent import Agent, Action, Observation

class Environment:

    size = 0
    agents = []

    def __init__(self, size, agents:list[Agent]):
        self.agents = agents
        self.size = size

    def send_observation(self, agent: Agent) -> Observation:
        pass

    def update(self):
        pass

    def act(self, action: Action, agent: Agent):
        pass

    def render(self):
        pass