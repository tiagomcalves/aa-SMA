import time
from abc import ABC, abstractmethod


class Request(ABC):
    def __init__(self):
        self.timestamp = time.time()

    @abstractmethod
    def to_dict(self) -> dict:
        pass

class Surroundings(Request):
    def __init__(self):
        super().__init__()

    def to_dict(self):
        return {
            "type": "surroundings",
            "timestamp": self.timestamp
        }
