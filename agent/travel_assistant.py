from abstract.fipa_responder import Responder


class TravelAssistant(Responder):

    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)

    def available_lines(self) -> None:

        avaliable_lines_query = """
            SELECT ?station ?line ?transport_type
            WHERE{
                ?station rdf:type :Station.
                ?station :partOfLine ?line.
                ?line :hasTransportType ?transport_type.
            }
        """

        result_query = self.concat_header(avaliable_lines_query)
        results = self.world.sparql_query(result_query)

        for station, line, transport in results:
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

        result_query = self.concat_header(avlbl_ct_lns)
        results = self.world.sparql_query(result_query)
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

        result_query = self.concat_header(full_line_query)
        results = self.world.sparql_query(result_query)
        print(list(results))