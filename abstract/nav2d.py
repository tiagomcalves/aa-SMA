from abc import abstractmethod
from dataclasses import dataclass

from abstract import Agent
from component.action import Action
from component.observation import Observation, ObservationType
from map.position import Position

@dataclass
class BaseAttributes:
    # Estado
    carrying = False
    last_attempted_action = None
    episode_ended = False

    # Sistema anti-loop para foraging
    pos_history = []
    stuck_counter = 0
    panic_mode = 0

    random_walk = True  # Sempre caminhada aleatória quando não tem comida
    wander_tendency = 0.8  # 80% chance de continuar na mesma direção


class Navigator2D(Agent):

    _position : Position
    _char : str

    @abstractmethod
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)
        self.problem = problem
        self.char = properties.get("char", "A")
        self._position = Position(*properties.get("starting_position", (0, 0)))

        self.base_attributes = BaseAttributes()


    def start_episode(self) -> None:
        self.base_attributes = BaseAttributes()

    def get_position(self) -> Position:
        return self._position

    def update_position(self, pos: Position):
        self._position = pos

    #@abstractmethod
    #def move(self, direction: Direction) -> None:
    #    pass

    def get_char(self) -> str:
        return self._char

    def use_sensor(self, post_action: bool) -> None:
        if post_action:
            #self.state.update_sensor_data(post_action, self._sensor.get_info(self))
            return

        curr_obs_bundle = self._sensor.get_info(self)
        #self.state.update_sensor_data(post_action, curr_obs_bundle)
        self.curr_observations.update({ObservationType.SURROUNDINGS : curr_obs_bundle.surroundings} if curr_obs_bundle.surroundings is not None else {})
        self.curr_observations.update({ObservationType.DIRECTION : curr_obs_bundle.directions} if curr_obs_bundle.directions is not None else {})
        self.curr_observations.update({ObservationType.LOCATION : curr_obs_bundle.location} if curr_obs_bundle.location is not None else {})

    @abstractmethod
    def observation(self, obs: Observation):
        pass

    @abstractmethod
    def act(self) -> Action:
        pass