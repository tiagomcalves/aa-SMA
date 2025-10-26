from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum

from rdflib import *
from owlready2 import *

from abstract.agent import Agent


class Responder(Agent):

    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)
        self.name = name
        self.world = World()
        self.RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

        self.onto = Responder.load_onto(self.name, self.world, properties["onto_file"])

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

    @staticmethod
    def print_onto_information(onto) -> None:
        print(onto.base_iri)
        for ind in onto.individuals():
            print(f"Individual: {ind.name}")
            print("  Types:", [c.name for c in ind.is_a])
            for prop in ind.get_properties():
                values = [getattr(v, "name", v) for v in prop[ind]]
                print(f"  - {prop.name}: {values}")

    @staticmethod
    def load_onto(agent_name: str, world: World, onto_file: str) -> Ontology:
        print(f"Agent \"{agent_name}\" is loading ontology file \"{onto_file}\"")
        onto = world.get_ontology(onto_file).load()
        sync_reasoner(world)
        Responder.materialize_superclasses(onto)
        Responder.print_onto_information(onto)
        return onto

    def concat_header(self, query_body: str) -> str:
        result =f"""
            PREFIX: <{self.onto.base_iri}>
            PREFIX rdf: <{self.RDF}>
            {query_body}
        """
        return result
