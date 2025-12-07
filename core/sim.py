from __future__ import annotations
from argparse import Namespace
from typing import final
import time

# --- IMPORTS DOS AGENTES (Crucial para o registo das classes) ---
import agent.phineas
import agent.ferb
# ----------------------------------------------------------------

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
        # Se for treino, steps instantâneos (0). Se for teste, usa o delay definido (ex: 100ms)
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
        log().vprint(agents_json_data)

        agents_ref_list = []
        agents_env_dict = {}

        for a_key, a_data in agents_json_data.items():

            # --- LÓGICA DE SELEÇÃO DE AGENTE (Treino vs Teste) ---
            # Identificar se o JSON ou o nome sugerem que é o Ferb
            is_ferb = "Ferb" in a_key or "ferb" in a_data.get("class", "")

            if args.train:
                # MODO TREINO:
                # Geralmente queremos treinar o Phineas.
                # Se for o Ferb, podemos ignorá-lo ou convertê-lo.
                # Aqui assumo que em treino forçamos todos a serem Phineas para acelerar a recolha de dados.
                a_data["class"] = "agent.phineas.Phineas"
                a_data["mode"] = "LEARNING"

                # Definir epsilon default se não existir
                if "epsilon" not in a_data:
                    a_data["epsilon"] = 0.1

            else:
                # MODO TESTE:
                # Aqui é CRUCIAL distinguir quem é quem para podermos comparar.

                if is_ferb:
                    # Se é o Ferb, deixamos ser o Ferb (Baseline)
                    a_data["class"] = "agent.ferb.Ferb"
                else:
                    # Se não é o Ferb, assumimos que é o nosso Agente Treinado (Phineas)
                    a_data["class"] = "agent.phineas.Phineas"
                    a_data["mode"] = "TEST"  # Usar o conhecimento adquirido (Exploit)

            # Criação do Agente usando a Factory
            # Nota: O a_data["class"] agora tem o caminho correto (ex: "agent.phineas.Phineas")
            _new_agent = Agent.create(args.problem, a_key, a_data)
            agents_ref_list.append(_new_agent)

            # Setup dos dados do Agente no Environment
            agents_env_dict[_new_agent] = Environment.setup_agent(a_key, a_data)

        import_sensor_handlers()

        # Instanciar Ambiente
        env = Environment(args.problem, loader.retrieve_data("environment"), args.renderer)
        env.register_agents(agents_env_dict)

        # Registar Handlers no Ambiente
        env_data = loader.retrieve_data("environment")
        if "sensor_handlers" in env_data:
            for handler in env_data["sensor_handlers"]:
                env.register_handler(handler)

        # Instalar Sensores nos Agentes
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

    def think(self) -> None:  # execute
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
            # 1. Remover agentes terminados
            for a in self._agents[:]:
                if a.status == AgentStatus.TERMINATED:
                    self.terminate_agent(a)
                    continue

            # Critério de paragem: Sem agentes
            if len(self._agents) == 0:
                break

            # Critério de segurança: Max Steps
            if self._scheduler.curr_step() > 10000:
                log().print("Max steps reached. Forcing termination.")
                break

            # 2. Update Environment (Dinâmica do mundo)
            self._env.update()

            # 3. Ciclo de Ação dos Agentes
            for a in self._agents:
                # O agente pensa e devolve uma Action
                action = a.act()

                # CORREÇÃO CRÍTICA AQUI:
                # O Ambiente recebe a ação e o agente, e decide o resultado
                self._env.act(action, a)

            # 4. Renderização e Logs
            if not self.args.train:
                log().print("Step: ", str(self._scheduler.curr_step()).rjust(3, '0'))
                if not self.args.headless:
                    self._env.render()
                time.sleep(self._STEP_SECONDS)
                log().print("-----------------------------------------------")

            # 5. Avançar relógio
            self.think()

        log().print("Simulation terminated in", self._scheduler.curr_step(), "steps")

    #   -------------------------------------------------------------------

    def _boot_output(self) -> None:
        _agents_list = "".join("\t\t - \"" + a.get_name() + "\"\n" for a in self._agents)

        steps_str = f" at {self.args.step} ms per step" if not self.args.train else ", step delays are disabled in training mode"
        r_str = f"display simulation in {'separate renderer window' if self.args.renderer else 'stdout'}"

        log().print(
            f"""------------------------------------------------
Initialize new Simulation of \"{self._name}\" at {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._curr_time))}

Running in {"training" if self.args.train else "testing"} mode{steps_str}
{("running headless" if self.args.headless else r_str) if not self.args.train else "running headless in training mode"}

Currently loaded {len(self._agents)} agents: 
{_agents_list}""")
        if not self.args.train and not self.args.headless:
            if not self.args.renderer:
                log().print("\nInitial State:")
            self._env.render()
        log().print("------------------------------------------------")


if __name__ == "__main__":
    print("You should run this script through main.py")
    exit(1)