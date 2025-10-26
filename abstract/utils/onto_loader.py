from owlready2 import World, Ontology, sync_reasoner, owl

def _materialize_superclasses(onto):
    added = 0
    for ind in onto.individuals():
        for cls in list(ind.is_a):
            for supercls in cls.ancestors():
                if supercls not in ind.is_a:
                    if supercls is not owl.Thing:
                        ind.is_a.append(supercls)
                        added += 1
                        print(f" Added {ind.name} as instance of {supercls.name}")


def _print_onto_information(onto) -> None:
    print(onto.base_iri)
    for ind in onto.individuals():
        print(f"Individual: {ind.name}")
        print("  Types:", [c.name for c in ind.is_a])
        for prop in ind.get_properties():
            values = [getattr(v, "name", v) for v in prop[ind]]
            print(f"  - {prop.name}: {values}")


def load_onto(agent_name: str, world: World, onto_file: str) -> Ontology:
    print(f"Agent \"{agent_name}\" is loading ontology file \"{onto_file}\"")
    onto = world.get_ontology(onto_file).load()
    sync_reasoner(world)
    _materialize_superclasses(onto)
    _print_onto_information(onto)
    return onto
