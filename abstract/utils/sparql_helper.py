from owlready2 import World, Ontology
import rdflib

def _concat_header(onto: Ontology, query_body: str) -> str:
    result = f"""
        PREFIX: <{onto.base_iri}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        {query_body}
    """
    return result

def sparql_query(world: World, onto: Ontology, query_body: str):
    query = _concat_header(onto, query_body)
    result = world.sparql_query(query)
    return result