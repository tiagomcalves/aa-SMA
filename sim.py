from __future__ import annotations

import datetime
from typing import final

import time

from env import Environment
from abstract.agent import Agent
from agent.travel_assistant import TravelAssistant

def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat() + "Z"

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

    travel_a = Agent.create("Travel Assistant", "agents.json")
    curr_agents.append(travel_a)
    env = Environment(5,curr_agents)

    while True :

        #print("My keys: ")
        print(" ::", now_iso(), )
        string = env.agents[0].concat_header("DESCRIBE \"available_lines\"")

        print(string)

        if isinstance(env.agents[0], TravelAssistant):
            env.agents[0].available_lines()

        #render_state

        time.sleep(0.75)
