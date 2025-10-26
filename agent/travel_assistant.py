from abstract import Responder
from abstract.utils import sparql_query


class TravelAssistant(Responder):

    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)


    def available_lines(self) -> None:

        available_lines_query = """
            SELECT ?station ?line ?transport_type
            WHERE{
                ?station rdf:type :Station.
                ?station :partOfLine ?line.
                ?line :hasTransportType ?transport_type.
            }
        """

        results = sparql_query(self.world, self.onto, available_lines_query)
        for station, line, transport in list(results):
            print(f"Station: {station.name} on {line.name} by {transport.name}")

    def available_city_lines(self, city:str):

        avlbl_ct_lns = f"""
            SELECT ?city ?station ?line
            WHERE{{
                ?station rdf:type :Station.
                ?station :partOfLine ?line.
                ?station :locatedIn ?city.
                FILTER regex(str(?city), "{city}").
            }}
        """

        results = sparql_query(self.world, self.onto, avlbl_ct_lns)
        print(list(results))

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