from __future__ import annotations
from argparse import Namespace
from typing import final, cast
import time
import json

from decorator import append

from env import Environment
from abstract import *

from agent.explorer import Explorer
from component.direction import Direction

def print_json(data: dict[str, str]) -> None:
    for name, info in data.items():
        print(name, info)

@final
class Simulator:

    def __init__(self, env: Environment, agents: list[Agent], args:Namespace):
        self.name = args.problem
        self.env = env
        self.agents = agents
        self.curr_time = time.time()
        self._boot_output()

    def _boot_output(self) -> None:
        _agents_list = "".join("\t\t - \"" + a.get_name() + "\"\n" for a in self.agents)
        print(
f"""------------------------------------------------
Initialize new Simulation of \"{self.name}\" at {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.curr_time))}

Currently loaded {len(self.agents)} agents: 
{_agents_list}
------------------------------------------------""")

    @staticmethod
    def create(args: Namespace) -> Simulator:
        print(args)
        agents_data = Simulator._load_agents(args.problem)
        #print_json(agents_data)
        agents = []

        for a_key, a_data in agents_data.items():
            #print(a_key, a_data)
            agents.append( Agent.create( a_key, a_data ))

        env = Environment(args.problem, len(agents), agents)
        return Simulator(env, agents, args)


    @staticmethod
    def _load_agents(file: str) -> dict[str, dict]:
        return Agent.load_agents_json(file)

    def list_agents(self) -> list[Agent]:
        return self.agents

    def think(self) -> None:    # execute
        pass

    def run(self) -> None:
        conv = "conv-{}".format(int(time.time()))

        while True:
            for agent in self.agents:
                casted = cast(Explorer, agent)
                casted.move(Direction.RIGHT)
                print(f"{casted.get_name()} current position: {casted.get_position()}")

            time.sleep(0.75)


if __name__ == "__main__":
    print("You should run this script through main.py")
    exit(1)