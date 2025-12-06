from __future__ import annotations
from argparse import Namespace
from typing import final
import time

from abstract import Agent
from abstract.agent import AgentStatus
from abstract.nav2d import Navigator2D
from core.logger import log
from core.loader import ConfigLoader
from core.scheduler import Scheduler
from core.env import Environment
from core.module_importer import import_sensor_handlers
from component.sensor.sensor import Sensor
from map.position import Position


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

    @staticmethod
    def create(args: Namespace) -> Simulator:
        log().vprint("Passed arguments to simulator:\n", args)
        loader = ConfigLoader(args.problem)

        agents_json_data = loader.retrieve_data("agents")
        log().vprint(agents_json_data)

        agents_ref_list = []
        agents_env_dict = {}

        for a_key, a_data in agents_json_data.items():
            a_data["class"] = "ferb.Ferb" if args.train else "ferb.Ferb"
            _new_agent = Agent.create(args.problem, a_key, a_data )
            agents_ref_list.append(_new_agent)
            agents_env_dict[_new_agent] = Environment.setup_agent(a_key, a_data)

        import_sensor_handlers()

        env = Environment(args.problem, loader.retrieve_data("environment"), args.renderer)
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

    def terminate_agent(self, agent) -> bool:
        if agent in self.list_agents():
            self.list_agents().remove(agent)
            log().print(agent.name, "terminated from Simulator")
            return True
        return False

    def run(self) -> None:
        conv = "conv-{}".format(int(time.time()))

        for a in self._agents:
            a.status = AgentStatus.RUNNING

        while True:

            log().print(conv)

            for a in self._agents[:]:  # hard-copy to avoid undefined behavior
                if a.status == AgentStatus.TERMINATED:
                    self.terminate_agent(a)
                    continue

            if len(self._agents) == 0:
                break

            for a in self._agents:
                action = a.act()
                self._env.validate_action(action)

            log().print("Step: ", str(self._scheduler.curr_step()).rjust(3, '0'))
            if not self.args.train:
                if not self.args.headless:
                    self._env.render()
                time.sleep(self._STEP_SECONDS)

            log().print("-----------------------------------------------")
            self.think()

        log().print("Simulation terminated in", self._scheduler.curr_step(), "steps")

#   -------------------------------------------------------------------

    def _boot_output(self) -> None:
        _agents_list = "".join("\t\t - \"" + a.get_name() + "\"\n" for a in self._agents)

        steps_str = f" at {self.args.step} ms per step" if not self.args.train else ", step delays are disabled in training mode"
        r_str = f"display simulation in {"separate renderer window" if self.args.renderer else "stdout"}"

        log().print(
f"""------------------------------------------------
Initialize new Simulation of \"{self._name}\" at {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._curr_time))}

Running in {"training" if self.args.train else "testing"} mode{steps_str}
{ ("running headless" if self.args.headless else r_str) if not self.args.train else "running headless in training mode"}

Currently loaded {len(self._agents)} agents: 
{_agents_list}""")
        if not self.args.train and not self.args.headless:
            if not self.args.renderer:
                log().print("\nInitial State:")
            self._env.render()
        log().print("------------------------------------------------")

#   -------------------------------------------------------------------

if __name__ == "__main__":
    print("You should run this script through main.py")
    exit(1)