import json

def parse_stations(file_path):
    """
    Parses a JSON file containing station data and returns a list of stations.

    Args:
        file_path (str): The path to the JSON file containing station data.

    Returns:
        list: A list of dictionaries, each representing a station.
    """
    with open(file_path, 'r') as file:
        data = json.load(file)

    stations = data.get('data', {}).get('supply', {}).get('stations', [])

    parsed_stations = []
    for station in stations:
        print(station["stationName"])
        parsed_stations.append([station["stationName"], station["location"]["lat"], station["location"]["lng"]])

    return parsed_stations


if __name__ == "__main__":
    stations = parse_stations("stations.json")
    print(stations)
    
