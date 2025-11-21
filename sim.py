from __future__ import annotations

import uuid
from typing import final

import datetime
import time

import requests

from env import Environment
from abstract import *

"""
def available_lines():
    msg = compose_request(conv, "planner@svc", "researcher@svc", "available_lines", "")
    res = send("http://localhost:8000/ingest", msg)
    query_res = res.get("reply").get("summary")
    #print("\n", query_res)
    print(query_res)

def available_city_lines(input):
    msg = compose_request(conv, "planner@svc", "researcher@svc", "available_city_lines", input)
    res = send("http://localhost:8000/ingest", msg)
    query_res = res.get("reply").get("summary")
    #print("\n", query_res)
    print(query_res)

def malicious_available_lines(args):
    msg = compose_request(conv, "planner@svc", "researcher@svc", "available_lines", args)
    res = send("http://localhost:8000/ingest", msg)
    query_res = res.get("reply").get("summary")
    #print("\n", query_res)
    print(query_res)
"""

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

    curr_agents =[]
    explorer_agent = Agent.create("2D Explorer", "agents.json")
    curr_agents.append(explorer_agent)
    env = Environment(10,curr_agents)

    simulator = Simulator(env, curr_agents)

    while True :
        explorer_agent.move(Direction.RIGHT)
        print(f"{explorer_agent.get_name()} current position: {explorer_agent.get_position()}")
        time.sleep(0.75)