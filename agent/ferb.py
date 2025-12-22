import random

from abstract.agent import AgentStatus
from abstract.nav2d import Navigator2D
from abstract.utils.policy import POLICY_REGISTRY
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from core.logger import log
from map.position import Position


class Ferb(Navigator2D):
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)
        #self.char = properties.get("char", "F")
        self.policy = POLICY_REGISTRY[problem]

        log().print(f"{name}: Inicializado para {problem} ({type(self.policy).__name__})")

    def start_episode(self) -> None:
        # # Estado
        super().start_episode()


    # ---------------------------------------------------
    # OBSERVAÇÃO
    # ---------------------------------------------------
    def observation(self, obs: Observation):
        if self.base_attributes.episode_ended: #se episodio acabou - n se mexe mais
            return

        reward = obs.payload.reward

        if obs.type == ObservationType.TERMINATE:
            if reward != 0.0:   # not a simulation shutdown
                self.register_reward(reward)

            self.status = AgentStatus.TERMINATED
            success = True if reward > 0.0 or self.ep.total_food_delivered > 0 else False
            self.end_episode(success)
            return

        self.register_reward(reward)

        if reward < 0.0:
            self.base_attributes.stuck_counter += 1
        elif reward > 0.0:
            #self._position = self._position + direction
            # Guarda histórico de posições
            self.base_attributes.pos_history.append(self._position)
            if len(self.base_attributes.pos_history) > 10:
                self.base_attributes.pos_history.pop(0)
            # Reseta contador de stuck se se moveu
            self.base_attributes.stuck_counter = 0


    def act(self) -> Action:
        if self.base_attributes.episode_ended: #se episodio acabou - n se mexe mais
            return self.action.wait()

        # Atualiza sensores
        if not self.has_observations():
            self.use_sensor(False)

        return self.policy.act(self.name, self.curr_observations, self.base_attributes, self.action)