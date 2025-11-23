import time
from abc import ABC, abstractmethod


class Request(ABC):
    def __init__(self):
        self.timestamp = time.time()

    @abstractmethod
    def to_dict(self) -> dict:
        pass

class Surroundings(Request):
    def __init__(self, pos):
        super().__init__()
        self.pos = pos

    def to_dict(self):
        return {
            "type": "surroundings",
            "position": self.pos.get(),
            "timestamp": self.timestamp
        }
