from abc import abstractmethod

from abstract import Agent
from component.action import Action
from component.observation import Observation, ObservationType
from map.position import Position

class Navigator2D(Agent):

    _position : Position
    _char : str

    @abstractmethod
    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)
        self._char = properties["char"]

    def get_position(self) -> Position:
        return self._position

    def update_position(self, pos: Position):
        self._position = pos

    #@abstractmethod
    #def move(self, direction: Direction) -> None:
    #    pass

    def get_char(self) -> str:
        return self._char

    def use_sensor(self) -> None:
        curr_obs_bundle = self._sensor.get_info(self)
        self.curr_observations.update({ObservationType.SURROUNDINGS : curr_obs_bundle.surroundings} if curr_obs_bundle.surroundings is not None else {})
        self.curr_observations.update({ObservationType.DIRECTION : curr_obs_bundle.directions} if curr_obs_bundle.directions is not None else {})
        self.curr_observations.update({ObservationType.LOCATION : curr_obs_bundle.location} if curr_obs_bundle.location is not None else {})

    @abstractmethod
    def observation(self, obs: Observation):
        pass

    @abstractmethod
    def act(self) -> Action:
        pass