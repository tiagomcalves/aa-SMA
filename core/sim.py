from __future__ import annotations
from argparse import Namespace
from typing import final
import time
import os

from abstract import Agent
from abstract.agent import AgentStatus
from core.logger import log
from core.loader import ConfigLoader
from core.scheduler import Scheduler
from core.env import Environment
from core.module_importer import import_sensor_handlers
from component.sensor.sensor import Sensor
from map.position import Position


@final
class Simulator:

    def __init__(self, env: Environment, agents: list[Agent], args: Namespace):
        self.args = args
        self._name = args.problem
        self._STEP_SECONDS = args.step / 1000 if not self.args.test else 0

        # Cria diretório de logs
        self._create_log_directory()

        # Define max steps
        self.max_steps = 1000
        self._scheduler = Scheduler(self.max_steps)

        self._env = env
        self._agents = agents
        self._curr_time = time.time()
        self._boot_output()

    def _create_log_directory(self):
        log_dir = f"logs/{self._name}"
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(f"{log_dir}/learning", exist_ok=True)
        os.makedirs(f"{log_dir}/test", exist_ok=True)

    @staticmethod
    def create(args: Namespace) -> Simulator:
        log().vprint("Passed arguments to simulator:\n", args)
        loader = ConfigLoader(args.problem)
        agents_json_data = loader.retrieve_data("agents")

        agents_ref_list = []
        agents_env_dict = {}

        for a_key, a_data in agents_json_data.items():
            is_ferb = "Ferb" in a_key or "ferb" in a_data.get("class", "")

            if not args.test:
                if "Phineas" in a_key or "phineas" in a_key.lower():
                    a_data["class"] = "agent.phineas.Phineas"
                    a_data["mode"] = "LEARNING"
                    if "epsilon" not in a_data: a_data["epsilon"] = 0.1
                else:
                    a_data["class"] = "agent.ferb.Ferb"
            else:
                if is_ferb:
                    a_data["class"] = "agent.ferb.Ferb"
                else:
                    a_data["class"] = "agent.phineas.Phineas"
                    a_data["mode"] = "TEST"

            _new_agent = Agent.create(args.problem, a_key, a_data)
            agents_ref_list.append(_new_agent)
            agents_env_dict[_new_agent] = Environment.setup_agent(a_key, a_data)

        import_sensor_handlers()

        env = Environment(args.problem, loader.retrieve_data("environment"), renderer=args.renderer)
        env.register_agents(agents_env_dict)

        env_data = loader.retrieve_data("environment")
        if "sensor_handlers" in env_data:
            for handler in env_data["sensor_handlers"]:
                env.register_handler(handler)

        sensor = Sensor(env)
        for agent in agents_ref_list:
            agent.set_env(env)
            agent.install(sensor)

        return Simulator(env, agents_ref_list, args)

    def list_agents(self) -> list[Agent]:
        return self._agents

    def think(self) -> None:
        self._scheduler.step()

    def terminate_agent(self, agent) -> bool:
        if agent in self.list_agents():
            self.list_agents().remove(agent)
            log().print(f"{agent.name} terminado")
            return True
        return False

    def run(self) -> None:
        for a in self._agents:
            if hasattr(a, "start_episode"): a.start_episode()
            a.status = AgentStatus.RUNNING

        while True:
            for a in self._agents[:]:
                if a.status == AgentStatus.TERMINATED:
                    self.terminate_agent(a)
                    continue

            if len(self._agents) == 0: break

            if self._scheduler.curr_step() >= self.max_steps:
                log().print(f"MAX STEPS ALCANÇADO: {self.max_steps}")
                break

            self._env.update()

            for a in self._agents:
                action = a.act()
                self._env.act(action, a)

            should_render = self.args.renderer and (not self.args.test or not self.args.headless)
            if should_render:
                self._env.render()
                if not self.args.test:
                    time.sleep(self._STEP_SECONDS)
                else:
                    time.sleep(0.001)

            if not self.args.test:
                log().print("Step: ", str(self._scheduler.curr_step()).rjust(3, '0'))
                log().print("-----------------------------------------------")

            self.think()

        log().print("============================================================")
        log().print("SIMULAÇÃO CONCLUÍDA")
        log().print(f"Total de steps: {self._scheduler.curr_step()}")

    def _boot_output(self) -> None:
        _agents_list = "".join("\t\t - \"" + a.get_name() + "\"\n" for a in self._agents)
        log().print(f"""------------------------------------------------
Simulation: \"{self._name}\"
Mode: {"TRAINING" if not self.args.test else "TESTING"}
Max Steps: {self.max_steps}
Logs: logs/{self._name}/
Agents: {len(self._agents)} loaded
{_agents_list}------------------------------------------------""")
        if self.args.renderer: self._env.render()


if __name__ == "__main__":
    print("Run via main.py")