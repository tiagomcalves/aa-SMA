# core/sim.py
from __future__ import annotations

import math
from argparse import Namespace
from typing import final
import time
import sys
import math
import os  # NOVO: para criar diretórios

# --- IMPORTS DOS AGENTES ---
import agent.phineas
import agent.ferb
# ---------------------------

from abstract import Agent
from abstract.agent import AgentStatus
from core.logger import log
from core.loader import ConfigLoader
from core.scheduler import Scheduler
from core.env import Environment
from core.module_importer import import_sensor_handlers
from component.sensor.sensor import Sensor


@final
class Simulator:

    def __init__(self, env: Environment, agents: list[Agent], args: Namespace):
        self.args = args
        self._scheduler = Scheduler(self._calculate_max_steps())
        self._name = args.problem
        self._STEP_SECONDS = args.step / 1000 if not self.args.train else 0
        self._env = env
        self._agents = agents
        self._curr_time = time.time()

        # NOVO: Cria diretório de logs específico para o problema
        self._create_log_directory()

        # NOVO: Calcula limite máximo de steps
        self.max_steps = self._calculate_max_steps()

        self._boot_output()

    def _create_log_directory(self):
        """Cria diretório de logs específico para o problema"""
        log_dir = f"logs/{self._name}"
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(f"{log_dir}/learning", exist_ok=True)
        os.makedirs(f"{log_dir}/test", exist_ok=True)
        log().vprint(f"📁 Logs directory created: {log_dir}")

    def _calculate_max_steps(self) -> int:
        """
        Calcula o limite máximo de steps baseado no tamanho do mapa.
        Para foraging: (8/8) * perímetro = perímetro completo
        Para lighthouse: (5/8) * perímetro
        Se erro no cálculo: 70 steps (default)
        """
        try:
            # Tenta obter tamanho do mapa
            grid_x, grid_y = 10, 10  # Default inicial

            # Tenta obter do loader
            try:
                loader = ConfigLoader(self._name)
                map_data = loader.retrieve_data("map")
                if map_data and "boundaries" in map_data:
                    boundaries = map_data["boundaries"]
                    grid_x, grid_y = boundaries[0], boundaries[1]
            except:
                pass  # Mantém default

            # Calcula perímetro
            perimeter = (grid_x * 2) + (grid_y * 2)

            # Determina fator baseado no problema
            problem_lower = self._name.lower()

            if "foraging" in problem_lower:
                factor = 8 / 8  # 1.0 - Perímetro completo
                problem_type = "foraging"
            elif "lighthouse" in problem_lower or "farol" in problem_lower:
                factor = 5 / 8  # 0.625 do perímetro
                problem_type = "lighthouse"
            else:
                # Para outros problemas, usa foraging como padrão
                factor = 8 / 8
                problem_type = "foraging (default)"

            # Calcula steps (arredonda para cima)
            max_steps = math.ceil(factor * perimeter)

            log().print(f"📏 MAX STEPS CALCULADO:")
            log().print(f"   Problema: {self._name}")
            log().print(f"   Tipo: {problem_type}")
            log().print(f"   Tamanho do mapa: {grid_x}x{grid_y}")
            log().print(f"   Perímetro: {perimeter}")
            log().print(f"   Fator: {factor}")
            log().print(f"   Máximo de steps: {max_steps}")

            return max_steps

        except Exception as e:
            log().print(f"⚠️  ERRO ao calcular max steps: {e}")
            log().print("   Usando valor default: 70 steps")
            return 70

    @staticmethod
    def create(args: Namespace) -> Simulator:
        log().vprint("Passed arguments to simulator:\n", args)
        loader = ConfigLoader(args.problem)

        agents_json_data = loader.retrieve_data("agents")

        agents_ref_list = []
        agents_env_dict = {}

        for a_key, a_data in agents_json_data.items():
            is_ferb = "Ferb" in a_key or "ferb" in a_data.get("class", "")

            # CRÍTICO: Determina modo baseado no argumento --train
            if args.train:
                # MODO TREINO: Apenas Phineas pode aprender
                if "Phineas" in a_key or "phineas" in a_key.lower():
                    a_data["class"] = "agent.phineas.Phineas"
                    a_data["mode"] = "LEARNING"
                    # Garante parâmetros de aprendizagem
                    if "epsilon" not in a_data:
                        a_data["epsilon"] = 0.1
                    if "learning_rate" not in a_data:
                        a_data["learning_rate"] = 0.1
                    if "discount_factor" not in a_data:
                        a_data["discount_factor"] = 0.9
                    log().print(f"🧠 {a_key}: Configurado para APRENDIZAGEM (modo treino)")
                else:
                    # Ferb mantém comportamento fixo mesmo em treino
                    a_data["class"] = "agent.ferb.Ferb"
                    log().print(f"🤖 {a_key}: Agente fixo (Ferb)")
            else:
                # MODO TESTE: Usa configuração do JSON
                if is_ferb:
                    a_data["class"] = "agent.ferb.Ferb"
                    log().print(f"🤖 {a_key}: Agente fixo (Ferb)")
                else:
                    a_data["class"] = "agent.phineas.Phineas"
                    a_data["mode"] = "TEST"  # Força modo TESTE
                    log().print(f"🧪 {a_key}: Configurado para TESTE")

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
            log().print(f"🏁 {agent.name} terminado")
            return True
        return False

    def run(self) -> None:
        # Inicia todos os agentes
        for a in self._agents:
            a.status = AgentStatus.RUNNING
            # Inicia episódio se o agente tiver o método
            if hasattr(a, 'start_episode'):
                a.start_episode()

        step = 0

        while True:
            step += 1

            # 1. Verifica limite de steps
            if step >= self.max_steps:
                log().print(f"\n{'=' * 50}")
                log().print(f"🏁 MAX STEPS ALCANÇADO: {step}/{self.max_steps}")
                log().print(f"{'=' * 50}")

                # Envia sinal de TERMINATE para todos os agentes
                for agent in self._agents:
                    if hasattr(agent, 'observation'):
                        # Usa o método correto para criar observação de término
                        from component.observation import Observation, ObservationType

                        # Cria payload simples para terminate
                        terminate_payload = {"action": None, "reward": 0.0}
                        terminate_obs = Observation(
                            type=ObservationType.TERMINATE,
                            payload=terminate_payload
                        )
                        agent.observation(terminate_obs)

                break

            # 2. Remover agentes terminados
            agents_to_remove = []
            for a in self._agents:
                if a.status == AgentStatus.TERMINATED:
                    agents_to_remove.append(a)

            for agent in agents_to_remove:
                self.terminate_agent(agent)

            # 3. Verifica se todos os agentes terminaram
            if len(self._agents) == 0:
                log().print(f"\n{'=' * 50}")
                log().print("🏁 Todos os agentes terminaram.")
                log().print(f"{'=' * 50}")
                break

            # 4. Log do step atual (apenas em modo normal)
            if not self.args.train and step % 10 == 0:
                log().vprint(f"📊 Step: {step}/{self.max_steps}")

            # 5. Update Environment
            self._env.update()

            # 6. Ação dos Agentes
            for a in self._agents:
                try:
                    action = a.act()
                    if action:
                        self._env.act(action, a)
                except Exception as e:
                    log().print(f"❌ Erro no agente {a.name}: {e}")

            # 7. Renderização e Delay
            should_render = self.args.renderer and (not self.args.train or not self.args.headless)

            if should_render:
                self._env.render()
                if not self.args.train:
                    time.sleep(self._STEP_SECONDS)
                else:
                    time.sleep(0.001)  # Delay pequeno mesmo em treino

            # 8. Print de progresso em modo treino
            if self.args.train and step % 100 == 0:
                log().print(f"📈 Treino: Step {step}/{self.max_steps}")
                # Mostra estatísticas dos agentes Phineas
                for agent in self._agents:
                    if hasattr(agent, 'name') and 'Phineas' in agent.name:
                        if hasattr(agent, 'episode_reward'):
                            log().print(f"   {agent.name}: Recompensa: {agent.episode_reward:.2f}")
                        if hasattr(agent, 'successful_returns'):
                            log().print(f"   {agent.name}: Entregues: {agent.successful_returns}")

            self.think()

        # FINALIZAÇÃO
        log().print(f"\n{'=' * 60}")
        log().print(f"🏁 SIMULAÇÃO CONCLUÍDA")
        log().print(f"{'=' * 60}")
        log().print(f"📊 Total de steps: {step}")
        log().print(f"📈 Limite calculado: {self.max_steps}")
        log().print(f"🎮 Modo: {'TREINO' if self.args.train else 'TESTE'}")

        # Estatísticas finais dos agentes
        for agent in self._agents:
            if hasattr(agent, 'name'):
                stats = []

                if hasattr(agent, 'successful_returns'):
                    stats.append(f"🍎 Entregues: {agent.successful_returns}")
                if hasattr(agent, 'total_food_collected'):
                    stats.append(f"📦 Coletadas: {agent.total_food_collected}")
                if hasattr(agent, 'episode_reward'):
                    stats.append(f"💰 Recompensa: {agent.episode_reward:.2f}")
                if hasattr(agent, 'current_episode'):
                    stats.append(f"📊 Episódio: {agent.current_episode}")

                if stats:
                    log().print(f"\n🤖 {agent.name}:")
                    for stat in stats:
                        log().print(f"   {stat}")

        log().print(f"{'=' * 60}")

        # Fecha todos os loggers
        log().close_all()

    def _boot_output(self) -> None:
        _agents_list = "".join("\t\t - \"" + a.get_name() + "\"\n" for a in self._agents)
        log().print(f"""------------------------------------------------
Simulation: \"{self._name}\"
Mode: {"TRAINING" if self.args.train else "TESTING"}
Max Steps: {self.max_steps} (calculado dinamicamente)
Logs: logs/{self._name}/
Agents: {len(self._agents)} loaded
{_agents_list}------------------------------------------------""")
        # Render inicial
        if self.args.renderer:
            self._env.render()


if __name__ == "__main__":
    print("Run via main.py")