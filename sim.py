from __future__ import annotations
from typing import final, cast

import datetime
import time

from env import Environment
from abstract import *

from agent.explorer import Explorer
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

    def think(self):    # execute
        pass


if __name__ == "__main__":
    conv = "conv-{}".format(int(time.time()))

    g_curr_agents =[]
    g_explorer_agent = cast(Explorer, Agent.create("2D Explorer", "agents.json"))
    g_curr_agents.append(g_explorer_agent)
    g_env = Environment(10,g_curr_agents)

    simulator = Simulator(g_env, g_curr_agents)

    while True :
        g_explorer_agent.move(Direction.RIGHT)
        print(f"{g_explorer_agent.get_name()} current position: {g_explorer_agent.get_position()}")
        time.sleep(0.75)