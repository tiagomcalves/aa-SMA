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

        #memoria espacial para ter nocao do ninho foraging

        # Para lighthouse - estimativa de posição do farol
        self.estimated_objective_position: Optional[Position] = None

        self.last_action = None

    def start_episode(self) -> None:
        # # Estado
        super().start_episode()

    def observation(self, obs: Observation):
        if self.base_attr.episode_ended: #se episodio acabou - n se mexe mais
            return

        reward = obs.payload.reward

        if obs.type == ObservationType.TERMINATE:
            if reward != 0.0:   # not a simulation shutdown
                self.register_reward(reward)

            self.base_attr.pos = self.base_attr.pos + self.last_action
            self.status = AgentStatus.TERMINATED
            success = True if reward > 0.0 or self.ep.total_food_delivered > 0 else False
            self.end_episode(success)
            return

        self.register_reward(reward)

        if obs.type == ObservationType.RESPONSE:

            if obs.payload.moved is False:
                self.base_attr.stuck_counter += 1
                return

            self.base_attr.stuck_counter = 0
            self.base_attr.pos_history.append(self.base_attr.pos)
            if len(self.base_attr.pos_history) > 10:
                self.base_attr.pos_history.pop(0)
                
            self.base_attr.pos = self.base_attr.pos + self.last_action

        return

    def act(self) -> Action:
        if self.base_attr.episode_ended: #se episodio acabou - n se mexe mais
            return self.action.wait()

        # Atualiza sensores
        self.use_sensor(False)



        self.last_action = self.policy.act(self.name, self.curr_observations, self.base_attr, self.action)
        return self.last_action