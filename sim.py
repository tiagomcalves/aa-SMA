from __future__ import annotations

from argparse import Namespace
from typing import final, cast

import datetime
import time
import argparse

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
    def create(problem: str, args: Namespace) -> Simulator:
        pass

    def list_agents(self) -> list[Agent]:
        return self.agents

    def think(self) -> None:    # execute
        pass

    def run(self) -> None:
        conv = "conv-{}".format(int(time.time()))

        g_explorer_agent = cast(Explorer, Agent.create("2D Explorer", "problem/lighthouse/agents.json"))
        self.agents.append(g_explorer_agent)
        self.env = Environment(10, self.agents)

        while True:
            g_explorer_agent.move(Direction.RIGHT)
            print(f"{g_explorer_agent.get_name()} current position: {g_explorer_agent.get_position()}")
            time.sleep(0.75)


if __name__ == "__main__":
    print("You should run this script through main.py")