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

        self._update_sensor(True)

        if obs.type == ObservationType.ACCEPTED:
            self.register_reward(obs.payload.reward)
            # Deteção via Reward (Auto-Pickup)
            if obs.payload.reward >= 40.0:
                if self.problem == "foraging":
                    if not self.base_attributes.carrying:
                        self.base_attributes.carrying = True
                    else:
                        self.base_attributes.carrying = False

            accepted_action = obs.payload.action

            if accepted_action.name == "move":
                direction = accepted_action.params.get("direction")
                if direction:
                    self._position = self._position + direction
                    # Guarda histórico de posições
                    self.base_attributes.pos_history.append(self._position)
                    if len(self.base_attributes.pos_history) > 10:
                        self.base_attributes.pos_history.pop(0)
                    # Reseta contador de stuck se se moveu
                    self.base_attributes.stuck_counter = 0

        elif obs.type == ObservationType.DENIED:
            self.register_reward(obs.payload.reward)
            self.base_attributes.stuck_counter += 1

        elif obs.type == ObservationType.TERMINATE:
            self.register_reward(obs.payload.reward)
            self.status = AgentStatus.TERMINATED
            success = True if obs.payload.reward > 0.0 else False
            self.end_episode(success)


    def _update_sensor(self, post_action: bool):
        self.curr_observations.clear()
        return self.use_sensor(post_action)


    def act(self) -> Action:
        if self.base_attributes.episode_ended: #se episodio acabou - n se mexe mais
            return self.action.wait()

        # Atualiza sensores
        if not self.has_observations():
            self._update_sensor(False)

        return self.policy.act(self.name, self.curr_observations, self.base_attributes, self.action)