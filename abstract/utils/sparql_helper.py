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

    results_list = []
    query = _concat_header(onto, query_body)

    try:
        rows = list(world.sparql_query(query))
        # value = a if cond else b
        # @tiago: I cant believe it myself either
        print(f"Found: {len(rows)} result{"s" if (len(rows) > 1) else ""}")
        for r in rows:
            vals = []
            for x in r:
                try:
                    ent = world[x]
                    vals.append(x)
                except Exception:
                    vals.append(x)

            results_list.append(vals)
        return results_list

    except Exception as e:
        print(f"   Query failed: {e}")
        return []
