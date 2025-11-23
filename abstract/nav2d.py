from abc import abstractmethod

from abstract import Agent
from component.action import Action
from component.direction import Direction
from component.observe import Observe
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

    #@abstractmethod
    #def move(self, direction: Direction) -> None:
    #    pass

    def get_char(self) -> str:
        return self._char

    def observation(self, obs: Observe):
        pass

    def act(self) -> Action:
        pass