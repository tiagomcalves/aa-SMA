from __future__ import annotations
from typing import final

import datetime
import time

from env import Environment
from abstract import *

from component.direction import Direction

@final
class Simulator:

    config: str

    def __init__(self, env: Environment, agents: list[Agent]):
        self.env = env
        self.agents = agents
        self.curr_time = time.time()


    @staticmethod
    def create(file: str) -> Simulator:
        pass

    def list_agents(self) -> list[Agent]:
        return self.agents

    def think(self):    # executeclear
        pass


if __name__ == "__main__":
    conv = "conv-{}".format(int(time.time()))

    curr_agents =[]
    explorer_agent = Agent.create("2D Explorer", "agents.json")
    curr_agents.append(explorer_agent)
    env = Environment(10,curr_agents)

    simulator = Simulator(env, curr_agents)

    while True :
        explorer_agent.move(Direction.RIGHT)
        print(f"{explorer_agent.get_name()} current position: {explorer_agent.get_position()}")
        time.sleep(0.75)