from abstract import Responder
from abstract.utils import sparql_query


class TravelAssistant(Responder):

    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)

        self.response_table = {
            "available_lines" : self.available_lines,
            "available_city_lines" : self.available_city_lines
        }

    def available_lines(self) -> str:

        available_lines_query = """
            SELECT ?station ?line ?transport_type
            WHERE{
                ?station rdf:type :Station.
                ?station :partOfLine ?line.
                ?line :hasTransportType ?transport_type.
            }
        """

        query_results = sparql_query(self.world, self.onto, available_lines_query)
        result = ""
        for station, line, transport in list(query_results):
            result += f"Station: {station.name} on {line.name} by {transport.name}\n"

        return result

    def available_city_lines(self, city:str) -> str:

        avlbl_ct_lns = f"""
            SELECT ?city ?station ?line
            WHERE{{
                ?station rdf:type :Station.
                ?station :partOfLine ?line.
                ?station :locatedIn ?city.
                FILTER regex(str(?city), "{city}").
            }}
        """

        query_results = sparql_query(self.world, self.onto, avlbl_ct_lns)
        result = ""
        for city, station, line in list(query_results):
            result += f"City: {city.name}, has station {station.name} with {line.name}\n"

        return result

    def full_line(self, line_name):

        full_line_query = f"""
            SELECT ?station ?line ?transport_type
            WHERE{{
                ?station rdf:type :Station.
                ?station :partOfLine ?line.
                ?line :hasTransportType ?transport_type.
                FILTER regex(str(?line), "{line_name}", "i").
            }}
        """
        #   FILTER regex(str(?line), "ARGUMENT STRING", "i").
        #   "i" — tells SPARQL to ignore case.

        results = sparql_query(self.world, self.onto, full_line_query)
        print(list(results))