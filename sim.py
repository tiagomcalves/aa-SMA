from __future__ import annotations
from typing import final

import random
import time

from env import Environment
from abstract_agent import Agent
from travel_assistant import TravelAssistant

@final
class Simulator:

    config: str
    env: Environment

    def __init__(self, file: str):
        self.agents = []
        self.curr_time = time.time()

    @staticmethod
    def create(file: str) -> Simulator:
        pass

    def list_agents(self) -> list[Agent]:
        return self.agents

    def think(self):    # execute
        pass


if __name__ == "__main__":

    curr_agents =[]

    travel_a = TravelAssistant("onto/travel.owx")
    curr_agents.append(travel_a)
    env = Environment(5,curr_agents)

    while True :

        #print("My keys: ")
        string = env.agents[0].concat_header("DESCRIBE \"available_lines\"")

        print(string)

        if isinstance(env.agents[0], TravelAssistant):
            env.agents[0].available_lines()

        #render_state

        time.sleep(0.75)
