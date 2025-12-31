from __future__ import annotations

import copy
from argparse import Namespace
from dataclasses import dataclass
from typing import final, Optional
import time
import os

from abstract import Agent
from abstract.agent import AgentStatus
from abstract.utils.action_builder import ActionBuilder
from component.observation import Observation
from core.logger import ReportLogger, log, HeatLogger
from core.loader import ConfigLoader
from core.scheduler import Scheduler
from core.env import Environment
from core.module_importer import import_sensor_handlers
from component.sensor.sensor import Sensor
from map.position import Position

@dataclass(frozen=True)
class EnvInitialState:
    env : Environment


@final
class Simulator:

    initial_state : Optional[EnvInitialState] = None

    def __init__(self, env: Environment, agents: list[Agent], args: Namespace, timestamp: float):
        self.args = args
        self._problem = args.problem
        self._STEP_SECONDS = args.step / 1000
        self._active_agents = 0

        # Define max steps
        self.max_steps = args.max_steps #terrible hack
        self._scheduler = Scheduler(self.max_steps, args.episodes)

        self._env = env
        self._agents = agents
        self._curr_time = timestamp

        # Cria diretório de logs
        self._create_log_directory()
        self.report_log = ReportLogger(timestamp, self._problem)
        max_x, max_y = self._env.get_map_size()
        self.heatmap_log = HeatLogger(timestamp, self._problem, max_x, max_y)

        self._boot_output()
        if not args.headless: self._env.render()

    def _create_log_directory(self):
        log_dir = f"logs/{self._problem}"
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(f"{log_dir}/learning", exist_ok=True)

    @staticmethod
    def create(args: Namespace, timestamp: float) -> Simulator:
        log().vprint("Passed arguments to simulator:\n", args)
        loader = ConfigLoader(args.problem)
        agents_json_data = loader.retrieve_data("agents")

        agents_ref_list = []
        agents_env_dict = {}

        for a_key, a_data in agents_json_data.items():
            a_data["timestamp"] = timestamp

            if "phineas" in a_key.lower():
                a_data["class"] = "agent.phineas.Phineas"
                a_data["mode"] = "TEST" if args.test else "LEARNING"
            else:
                a_data["class"] = "agent.ferb.Ferb"

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

        if "max_steps" in env_data:
            setattr(args, "max_steps", env_data["max_steps"])   #terrible hack

        Simulator.initial_state = EnvInitialState(env.clone())
        return Simulator(env, agents_ref_list, args, timestamp)

    def list_agents(self) -> list[Agent]:
        return self._agents

    def think(self) -> None:
        self._scheduler.step()

    def tell_agents_to_terminate(self):
        for a in self._agents:
            self._env.send_observation(a, Observation.terminate(ActionBuilder(a).wait(), 0.0))

    def terminate_agent(self, agent) -> bool:
        if agent in self.list_agents():

            if self._scheduler.is_last_episode():
                self.list_agents().remove(agent)
                log().print(f"{agent.name} terminado")
                self.report_log.retrieve_session_data(agent, self._scheduler.curr_episode()+1)

            agent.status = AgentStatus.IDLE
            self._active_agents -= 1
            return True
        return False
    
    def terminate_all_agents(self):
        for a in self._agents[:]:
            if a.status == AgentStatus.TERMINATED:
                self.terminate_agent(a)
                continue

    def run(self) -> None:

        while not self._scheduler.out_of_episode():

            log().print("============================================================")
            log().print(f"Episódio {self._scheduler.curr_episode() + 1}")

            sensor = Sensor(self._env)

            for a in self._agents:
                a.start_episode()
                a.status = AgentStatus.RUNNING
                self._active_agents += 1
                # (re)install sensor at the beginning of each episode
                # a.set_env(self._env)
                a.install(sensor)


            while not self._scheduler.out_of_steps():
                for a in self._agents[:]:
                    if a.status == AgentStatus.TERMINATED:
                        self.terminate_agent(a)
                        continue

                if self._active_agents == 0: break

                self._env.update()

                for a in self._agents:
                    action = a.act()
                    self._env.act(action, a)


                should_render = not self.args.headless
                if should_render:
                    self._env.render()
                    log().print("Step: ", str(self._scheduler.curr_step()).rjust(3, '0'))
                    log().print("-----------------------------------------------")
                    time.sleep(self._STEP_SECONDS)

                self.think()

            self.tell_agents_to_terminate()
            self.terminate_all_agents()

            log().print("============================================================")
            log().print(f"EPISODIO CONCLUÍDO {"(MAX STEPS ALCANÇADO)" if self._scheduler.out_of_steps() else ""}")
            log().print(f"Total de steps: {self._scheduler.curr_step()}")

            self.heatmap_log.collect(self._env.retrieve_visited_positions())
            self._scheduler.next_episode()
            if not self._scheduler.out_of_episode():
                self._env = self.initial_state.env.clone()

        print("agentes ativos:", self._active_agents)
        log().print(f"SIMULAÇÃO CONCLUÍDA")
        self.report_log.close()
        self.heatmap_log.close()


    def _boot_output(self) -> None:
        _agents_list = "".join("\t\t - \"" + a.get_name() + "\"\n" for a in self._agents)
        log().print(f"""------------------------------------------------
Simulation: \"{self._problem}\"
Mode: {"TESTING" if self.args.test else "LEARNING"}
Max Steps: {self.max_steps}
Logs: logs/{self._problem}/
Agents: {len(self._agents)} loaded
{_agents_list}------------------------------------------------""")
        if self.args.renderer: self._env.render()


if __name__ == "__main__":
    print("Run via main.py")