from __future__ import annotations

from owlready2 import World, Ontology
from abstract.utils import *
from abstract import Agent

class Responder(Agent):

    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)
        self.name = name
        self.world = World()
        self.onto = load_onto(self.name, self.world, properties["onto_file"])

