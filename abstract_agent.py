from __future__ import annotations
from abc import ABC, abstractmethod
from rdflib import *
from owlready2 import *

class Action:
    pass

class Observation:
    pass

class Sensor:
    pass


class Agent(ABC):

    @abstractmethod
    def __init__(self, onto_file:str, materialize_supercls=True):

        self.world = World()
        self.RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

        self.onto = self.world.get_ontology(onto_file).load()

        if materialize_supercls:
            self.materialize_superclasses(self.onto)

    @staticmethod
    def materialize_superclasses(onto):
        added = 0
        for ind in onto.individuals():
            for cls in list(ind.is_a):
                for supercls in cls.ancestors():
                    if supercls not in ind.is_a:
                        if supercls is not owl.Thing:
                            ind.is_a.append(supercls)
                            added += 1
                            print(f" Added {ind.name} as instance of {supercls.name}")

    def concat_header(self, query_body: str) -> str:
        result =f"""
            PREFIX: <{self.onto.base_iri}>
            PREFIX rdf: <{self.RDF}>
            {query_body}
        """
        return result

    def observation(self, obs: Observation):
        pass

    def act(self) -> Action:
        pass

    def check_current_state(self, reward: float):
        pass

    def install(self, sensor: Sensor):
        pass

    def communicate(self, msg: str, sender: Agent):   # thanks to "import annotations"
        pass

    def available_lines(self):
        pass
