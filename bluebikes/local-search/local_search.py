import os
from bluebikes.tsp.helpers import load_route, load_stations, load_distance_matrix, format_python_tsp_route, write_route_to_csv
from bluebikes.tsp.get_directions import main as create_map_w_directions
from python_tsp.heuristics import solve_tsp_local_search

ROUTE_FILE = "outputs/routes/shortest_distance_route_ps2.csv"
PETURBATION_SCHEME = "ps6"
OUTPUT_FILE = ROUTE_FILE.replace(".", f"_{PETURBATION_SCHEME}.")
max_stations = None

stations = load_stations()
selected_stations = stations[:max_stations] if max_stations else stations
distance_matrix = load_distance_matrix("distance")
selected_matrix = distance_matrix[:max_stations, :max_stations] if max_stations else distance_matrix

last_route = load_route(ROUTE_FILE) if os.path.exists(ROUTE_FILE) else None
x0 = [waypoint["station_id"] for waypoint in last_route] if last_route and len(last_route) == len(selected_stations) else None

raw_route, _  = solve_tsp_local_search(distance_matrix, x0, perturbation_scheme=PETURBATION_SCHEME)
route = format_python_tsp_route(selected_stations, raw_route)
write_route_to_csv(route, OUTPUT_FILE)
create_map_w_directions(OUTPUT_FILE)