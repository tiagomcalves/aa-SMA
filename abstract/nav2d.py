from abc import abstractmethod
from dataclasses import dataclass, replace, field
from typing import Optional

from abstract import Agent
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from map.position import Position

@dataclass
class BaseAttributes:
    # Estado
    pos : Position = Position(0, 0)
    last_attempted_action : bool = None
    episode_ended : bool = False
    carrying : bool = False
    known_nest_pos : Optional[Position] = None

    # Sistema anti-loop para foraging
    pos_history : list = field(default_factory=list)
    stuck_counter : int = 0
    panic_mode : int = 0

    follow_wall : bool = False
    saved_directions : tuple[Direction,Direction] = (None,None)

    random_walk : bool = True  # Sempre caminhada aleatória quando não tem comida
    wander_tendency : float = 0.8  # 80% chance de continuar na mesma direção


@dataclass
class CurrEpisode:
    current : int = 0
    reward : float = 0.0
    steps : int = 0
    last_extrinsic_reward : float = 0.0
    success : bool = False

    #foraging related
    total_food_collected : int = 0
    total_food_delivered : int = 0
    successful_returns : int = 0

    # round(episode_data.get('avg_reward_last_10', 0.0), 4),
    # round(episode_data.get('success_rate_last_10', 0.0), 4)

@dataclass
class CurrLearningEpisode(CurrEpisode):
    # learning
    epsilon : float = 0.0
    epsilon_decay : float = 0.0
    learning_rate : float = 0.0,
    discount_factor : float = 0.0,
    q_table_size : int = 0


@dataclass
class SessionData:
    steps_per_ep : list = field(default_factory=list)
    rewards : list = field(default_factory=list)
    successes : list = field(default_factory=list)


class Navigator2D(Agent):

    _char : str

    @abstractmethod
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)
        self.problem = problem
        self.char = properties.get("char", "A")

        self.base_attr = BaseAttributes()
        self.ep = CurrEpisode()
        self.session = SessionData()


    def start_episode(self) -> None:
        self.base_attr = BaseAttributes()
        self.ep = replace(CurrEpisode(), current=self.ep.current+1)

    def end_episode(self, success: bool = False):
        # Verifica se já terminou (evita chamadas duplicadas)
        if self.base_attr.episode_ended:  # se episodio acabou - n se mexe mais
            return

        self.base_attr.episode_ended = True
        self.ep.success = success

        # Guarda no histórico
        self.session.rewards.append(self.ep.reward)
        self.session.steps_per_ep.append(self.ep.steps)
        self.session.successes.append(1 if success else 0)


    def get_pos(self) -> Position:
        return self.base_attr.pos

    def set_pos(self, pos: Position):
        self.base_attr.pos = pos

    def get_char(self) -> str:
        return self._char

    def use_sensor(self, post_action: bool = False) -> None:
        self.curr_observations.clear()
        if post_action:
            #self.state.update_sensor_data(post_action, self._sensor.get_info(self))
            return

        curr_obs_bundle = self._sensor.get_info(self)
        #self.state.update_sensor_data(post_action, curr_obs_bundle)
        self.curr_observations.update({ObservationType.SURROUNDINGS : curr_obs_bundle.surroundings})
        self.curr_observations.update({ObservationType.DIRECTION : curr_obs_bundle.directions})
        self.curr_observations.update({ObservationType.LOCATION : curr_obs_bundle.location})

    @abstractmethod
    def observation(self, obs: Observation):
        pass

    @abstractmethod
    def act(self) -> Action:
        pass

    def register_reward(self, reward: float):
        self.ep.reward += reward
        self.ep.steps += 1
        self.ep.last_extrinsic_reward = reward