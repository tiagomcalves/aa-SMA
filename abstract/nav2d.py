from abc import abstractmethod

from abstract import Agent
from component.action import Action
from component.observation import Observation
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

    @abstractmethod
    def use_sensor(self) -> Observation:
        pass

    @abstractmethod
    def observation(self, obs: Observation):
        pass

    @abstractmethod
    def act(self) -> Action:
        pass