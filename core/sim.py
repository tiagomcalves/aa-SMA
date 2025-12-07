from __future__ import annotations
from argparse import Namespace
from typing import final
import time
import sys

# --- IMPORTS DOS AGENTES ---
import agent.phineas
import agent.ferb
# ---------------------------

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

    def __init__(self, env: Environment, agents: list[Agent], args: Namespace):
        self.args = args
        self._scheduler = Scheduler()
        self._name = args.problem
        self._STEP_SECONDS = args.step / 1000 if not args.train else 0
        self._env = env
        self._agents = agents
        self._curr_time = time.time()
        self._boot_output()

    @staticmethod
    def create(args: Namespace) -> Simulator:
        log().vprint("Passed arguments to simulator:\n", args)
        loader = ConfigLoader(args.problem)

        agents_json_data = loader.retrieve_data("agents")

        agents_ref_list = []
        agents_env_dict = {}

        for a_key, a_data in agents_json_data.items():
            is_ferb = "Ferb" in a_key or "ferb" in a_data.get("class", "")

            if args.train:
                # MODO TREINO: Forçar Phineas
                a_data["class"] = "agent.phineas.Phineas"
                a_data["mode"] = "LEARNING"
                if "epsilon" not in a_data:
                    a_data["epsilon"] = 0.1
            else:
                # MODO TESTE
                if is_ferb:
                    a_data["class"] = "agent.ferb.Ferb"
                else:
                    a_data["class"] = "agent.phineas.Phineas"
                    a_data["mode"] = "TEST"

            _new_agent = Agent.create(args.problem, a_key, a_data)
            agents_ref_list.append(_new_agent)
            agents_env_dict[_new_agent] = Environment.setup_agent(a_key, a_data)

        import_sensor_handlers()

        # Instanciar Ambiente com renderer flag correta
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
            log().print(agent.name, "terminated from Simulator")
            return True
        return False

    def run(self) -> None:
        for a in self._agents:
            a.status = AgentStatus.RUNNING

        while True:
            # 1. Remover agentes terminados
            for a in self._agents[:]:
                if a.status == AgentStatus.TERMINATED:
                    self.terminate_agent(a)
                    continue

            if len(self._agents) == 0:
                break

            if self._scheduler.curr_step() > 20000:  # Aumentei limite para 20k
                log().print("Max steps reached. Forcing termination.")
                break

            # 2. Update Environment
            self._env.update()

            # 3. Ação dos Agentes
            for a in self._agents:
                action = a.act()
                self._env.act(action, a)

            # 4. Renderização e Logs
            # Se a flag --renderer (-r) estiver ativa, desenha SEMPRE,
            # exceto se estiver em modo treino E headless.
            should_render = self.args.renderer and (not self.args.train or not self.args.headless)

            if should_render:
                self._env.render()
                if not self.args.train:
                    time.sleep(self._STEP_SECONDS)
                else:
                    time.sleep(0.001)

            if not self.args.train:
                log().print("Step: ", str(self._scheduler.curr_step()).rjust(3, '0'))
                log().print("-----------------------------------------------")

            self.think()

        log().print("Simulation terminated in", self._scheduler.curr_step(), "steps")

    def _boot_output(self) -> None:
        _agents_list = "".join("\t\t - \"" + a.get_name() + "\"\n" for a in self._agents)
        log().print(f"""------------------------------------------------
Simulation: \"{self._name}\"
Mode: {"TRAINING" if self.args.train else "TESTING"}
Agents: {len(self._agents)} loaded
{_agents_list}------------------------------------------------""")
        # Render inicial
        if self.args.renderer:
            self._env.render()


if __name__ == "__main__":
    print("Run via main.py")