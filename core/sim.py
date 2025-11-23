from __future__ import annotations
from argparse import Namespace
from typing import final, cast
import time

from abstract.nav2d import Navigator2D
from core.scheduler import Scheduler
from core.env import Environment
from abstract import *

from component.sensor import Sensor
from map.position import Position


def print_json(data: dict[str, str]) -> None:
    for name, info in data.items():
        print(name, info)

@final
class Simulator:

    def __init__(self, env: Environment, agents: list[Agent], args:Namespace):
        self.args = args
        self._scheduler = Scheduler()
        self._name = args.problem
        self._STEP_SECONDS = args.step / 1000
        self._env = env
        self._agents = agents
        self._curr_time = time.time()
        self._boot_output()

    def _boot_output(self) -> None:
        _agents_list = "".join("\t\t - \"" + a.get_name() + "\"\n" for a in self._agents)
        print(
f"""------------------------------------------------
Initialize new Simulation of \"{self._name}\" at {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._curr_time))}

Currently loaded {len(self._agents)} agents: 
{_agents_list}
------------------------------------------------""")

    @staticmethod
    def create(args: Namespace) -> Simulator:
        print(args)
        agents_data = Simulator._load_agents(args.problem)
        #print_json(agents_data)
        agents = []

        for a_key, a_data in agents_data.items():
            agents.append( Agent.create( a_key, a_data ))

        env = Environment(args.problem)

        sensor = Sensor(env)
        for agent in agents:
            agent.install(sensor)

        return Simulator(env, agents, args)


    @staticmethod
    def _load_agents(file: str) -> dict[str, dict]:
        return Agent.load_agents_json(file)

    def _pack_agents_positions(self) -> dict[Position, str]:
        positions = {}

        for a in self._agents:
            if not isinstance(a, Navigator2D):
                continue

            positions[a.get_position()] = a.get_char()

        return positions

    def list_agents(self) -> list[Agent]:
        return self._agents

    def think(self) -> None:    # execute
        self._scheduler.step()

    def run(self) -> None:
        conv = "conv-{}".format(int(time.time()))

        while True:

            print(conv)
            if not self.args.headless:
                self._env.render(self._pack_agents_positions())
                time.sleep(self._STEP_SECONDS)

            self.think()


if __name__ == "__main__":
    print("You should run this script through main.py")
    exit(1)