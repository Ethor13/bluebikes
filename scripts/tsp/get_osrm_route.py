import requests
from helpers import load_stations, write_route_to_csv, create_interactive_map

OSRM_URL = "http://localhost:5000/trip/v1/bicycle"
OUTPUT_FILE = "outputs/routes/osrm_route.csv"

def format_osrm_route(data, stations):
    route = []
    for idx, waypoint in enumerate(data["waypoints"]):
        station = stations[idx]

        route.append({
            "stop_number": waypoint["waypoint_index"],
            "station_name": station["station_name"],
            "lat": station["lat"],
            "lng": station["lng"],
            "distance_to_next_km": round(waypoint["distance"], 3)
        })


    route.sort(key=lambda x: x["stop_number"])  # Sort by waypoint index

    cumulative_distance = 0.0
    for idx, waypoint in enumerate(route):
        route[idx]["cumulative_distance_km"] = round(cumulative_distance, 3)
        cumulative_distance += waypoint["distance_to_next_km"]

    return route

def main(max_stations=None):
    stations = load_stations()
    selected_stations = stations[:max_stations] if max_stations else stations 

    url = f"{OSRM_URL}/{';'.join([f'{s['lng']},{s['lat']}' for s in selected_stations])}"

    r = requests.get(url)
    r.raise_for_status()
    raw_route = r.json()

    route = format_osrm_route(raw_route, selected_stations)
    write_route_to_csv(route, OUTPUT_FILE)
    create_interactive_map(selected_stations, route, 'outputs/maps/osrm_map.html')


if __name__ == "__main__":
    main(5)