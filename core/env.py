from typing import Optional

from abstract.agent import Agent
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from component.sensor.registry import HANDLER_REGISTRY
from core.logger import log
from core.renderer.r_handle import Renderer
from map.entity import AgentData, MapEntity
from map.map import Map
from map.position import Position


class Environment:
    _agent_data: dict[Agent, AgentData]
    renderer: Optional[Renderer] = None

    def __init__(self, problem: str, data: dict, renderer=True):
        self._handlers = {}
        self.problem_type = problem  # Guardar o tipo de problema (lighthouse vs foraging)
        if renderer:
            self.renderer = Renderer()

        self._map = Map(problem, data["map"], self)
        self._agent_data = {}  # Inicializa vazio para evitar erros antes do registo

    def register_handler(self, request_type: str):
        handler_cls = HANDLER_REGISTRY.get(request_type)
        if handler_cls is None:
            raise ValueError(f"No sensor handler registered with name '{request_type}'")
        handler_instance = handler_cls()
        self._handlers[request_type] = handler_instance

    @staticmethod
    def setup_agent(name: str, data: dict) -> AgentData:
        # Adiciona flag 'carrying' para o problema de Recoleção
        agent_data = AgentData(data["char"], name, Position(*data["starting_position"]), 0.0)
        agent_data.carrying = None  # None ou valor do recurso
        return agent_data

    def register_agents(self, agents_dict: dict[Agent, AgentData]) -> None:
        self._agent_data = agents_dict

    def remove_agent(self, agent: Agent):
        log().print(f"Env: remove agent {agent.name}")
        if agent in self._agent_data:
            self._agent_data.pop(agent)

    def send_observation(self, agent: Agent, obs: Observation) -> Observation:
        agent.observation(obs)

        if obs.type == ObservationType.TERMINATE:
            self.remove_agent(agent)

        return obs

    def update(self):
        """
        Atualiza a dinâmica do ambiente (ex: respawn de recursos).
        """
        pass

    def act(self, action: Action, agent: Agent):
        """
        Encaminha a ação para a lógica correta.
        """
        if action.name == "move":
            self.validate_move(action)
        elif action.name == "pick":
            self.agent_pick(action)
        elif action.name == "drop":
            self.agent_drop(action)
        else:
            self.send_observation(agent, Observation.denied(action, 0.0))

    def _pack_agents_positions(self) -> dict[Position, str]:
        positions = {}
        for agent, data in self._agent_data.items():
            if not isinstance(agent, Navigator2D):
                continue
            positions[data.pos] = data.char
        return positions

    def render(self):
        positions = self._pack_agents_positions()

        # --- LINHA DE DEBUG (Apaga depois de confirmar que funciona) ---
        log().print(f"DEBUG RENDER: Agentes em {list(positions.keys())}")
        # ---------------------------------------------------------------

        self._map.render(positions)

    def get_objectives(self):
        return self._map.get_entity_by_name("OBJECTIVE")

    def get_tile_data(self, pos: Position) -> MapEntity:
        return self._map.get_position_data(pos)

    def get_tile_as_str(self, pos: Position) -> str:
        data = self._map.get_position_data(pos)
        if data:
            return data.name.upper()
        return "EMPTY"

    def validate_move(self, action: Action):
        """ Lógica de Movimento e Colisões """
        agent = action.agent
        direction = action.params.get("direction")

        # 1. Agente decidiu ficar parado
        if direction == Direction.NONE:
            log().vprint("agent ", self._agent_data[agent].name, " is choosing to stand still")
            self.send_observation(agent, Observation.denied(action, -1.0))
            return

        current_pos = self._agent_data[agent].pos
        target_pos = current_pos + direction

        tile = self.get_tile_data(target_pos)

        # 2. Verificar Limites e Obstáculos Estáticos
        if tile is None:
            self.send_observation(agent, Observation.denied(action, -1.0))
            return
        elif tile.collideable:
            log().vprint(f"Agent {self._agent_data[agent].name} hit wall")
            self.send_observation(agent, Observation.denied(action, -0.5))
            return

        # 3. Verificar Colisão com outros Agentes
        for o_agent, o_data in self._agent_data.items():
            if o_agent is agent: continue
            if o_data.pos == target_pos:
                log().vprint(f"Agent {self._agent_data[agent].name} bumped into {o_data.name}")
                self.send_observation(agent, Observation.denied(action, -0.2))
                return

        # 4. Movimento Válido
        self._agent_data.get(agent).pos = target_pos

        # --- CORREÇÃO: Penalização por passo (-1.0) para incentivar rapidez ---
        self.send_observation(agent, Observation.accepted(action, -1.0))

    def agent_pick(self, action: Action):
        agent_data = self._agent_data[action.agent]
        tile = self.get_tile_data(agent_data.pos)

        if tile is None:
            self.send_observation(action.agent, Observation.none())
            return

        log().vprint(f"env: {action.agent.name} picking at {tile.name}")

        # --- CASO 1: FAROL (LIGHTHOUSE) ---
        if tile.name.upper() == "OBJECTIVE":
            log().print(f"!!! {action.agent.name} REACHED OBJECTIVE !!!")
            # Recompensa +100 conforme relatório
            self.send_observation(action.agent, Observation.terminate(action, 100.0))
            return

        # --- CASO 2: RECOLEÇÃO (FORAGING) ---
        # Se for Comida ou Recurso
        if tile.name.upper() in ["FOOD", "RESOURCE", "GARBAGE"]:
            if agent_data.carrying is None:
                agent_data.carrying = 1.0  # Valor base do recurso
                # Nota: Idealmente removerias o item do mapa aqui (self._map.remove_item(pos))

                # Apanhar não dá recompensa imediata, só depositar
                self.send_observation(action.agent, Observation.accepted(action, -0.1))
            else:
                # Já está carregado
                self.send_observation(action.agent, Observation.denied(action, -0.1))
            return

        self.send_observation(action.agent, Observation.denied(action, -0.1))

    def agent_drop(self, action: Action):
        """ Lógica para depositar recursos no Ninho (Foraging) """
        agent_data = self._agent_data[action.agent]
        tile = self.get_tile_data(agent_data.pos)

        # Só pode largar se tiver algo e estiver no Ninho
        if agent_data.carrying is not None and tile.name.upper() == "NEST":
            # Fórmula do Relatório: R = Deposito * Valor
            reward = 10.0 * agent_data.carrying

            agent_data.carrying = None  # Esvazia inventário
            log().print(f"{action.agent.name} deposited resource! Reward: {reward}")

            self.send_observation(action.agent, Observation.accepted(action, reward))
        else:
            self.send_observation(action.agent, Observation.denied(action, -0.1))

    def serve_data(self, agent: Agent) -> dict[str, Observation]:
        if agent not in self._agent_data: return {}
        sensor_data = {}
        for handler_name, handler_inst in self._handlers.items():
            sensor_data[handler_name] = handler_inst.handle(self._agent_data[agent], self)
        return sensor_data

    def get_entities_by_type(self, entity_name: str) -> dict:
        """ Devolve todas as posições de entidades com um determinado nome (ex: 'FOOD', 'NEST') """
        # Reutiliza a lógica do get_entity_by_name do Map
        return self._map.get_entity_by_name(entity_name)
