from __future__ import annotations
from argparse import Namespace
from sched import scheduler
from typing import final
import time

from abstract import Agent
from abstract.nav2d import Navigator2D
from core.loader import ConfigLoader
from core.module_importer import import_sensor_handlers
from core.scheduler import Scheduler
from core.env import Environment
from component.sensor.sensor import Sensor
from map.position import Position
from core.logger import log


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
        log().print(
f"""------------------------------------------------
Initialize new Simulation of \"{self._name}\" at {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._curr_time))}

Currently loaded {len(self._agents)} agents: 
{_agents_list}
------------------------------------------------""")

    @staticmethod
    def create(args: Namespace) -> Simulator:
        log().vprint("Passed arguments to simulator:\n", args)
        loader = ConfigLoader(args.problem)

        agents_json_data = loader.retrieve_data("agents")
        log().vprint(agents_json_data)

        agents_ref_list = []
        agents_env_dict = {}

        for a_key, a_data in agents_json_data.items():
            _new_agent = Agent.create( a_key, a_data )
            agents_ref_list.append(_new_agent)
            agents_env_dict[_new_agent] = Environment.setup_agent(a_key, a_data)

        import_sensor_handlers()

        env = Environment(args.problem, loader.retrieve_data("environment"))
        env.register_agents(agents_env_dict)

        for handler in loader.retrieve_data("environment")["sensor_handlers"]:
            env.register_handler(handler)

        sensor = Sensor(env)

        for agent in agents_ref_list:
            agent.set_env(env)
            agent.install(sensor)

        return Simulator(env, agents_ref_list, args)

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

            log().print(conv)

            for a in self._agents:
                a.observation(a.use_sensor())
                action = a.act()
                self._env.validate_action(action)

            log().print("-----------------------------------------------")
            log().print("Step: ", str(self._scheduler.curr_step()).rjust(3, '0'))
            if not self.args.headless:
                self._env.render()
                time.sleep(self._STEP_SECONDS)

            log().print("-----------------------------------------------")
            self.think()


if __name__ == "__main__":
    print("You should run this script through main.py")
    exit(1)