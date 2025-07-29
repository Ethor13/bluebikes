import os
from python_tsp.heuristics import solve_tsp_simulated_annealing
from helpers import load_stations, load_distance_matrix, format_python_tsp_route, write_route_to_csv, load_route
from get_directions import main as create_map_w_directions

ROUTE_FILE = "outputs/routes/shortest_distance_route.csv"

def get_route_order(route, stations):
    ...

def main(max_stations=None):
    """
    Run TSP analysis on a set of stations with optional visualization.
    
    Args:
        stations (list): List of all stations [name, lat, lng]
        max_stations (int): Maximum number of stations to include in analysis
        visualize (bool): Whether to create visualizations
    
    Returns:
        tuple: (selected_stations, route, total_distance)
    """
    stations = load_stations()
    selected_stations = stations[:max_stations] if max_stations else stations
    distance_matrix = load_distance_matrix("distance")
    selected_matrix = distance_matrix[:max_stations, :max_stations] if max_stations else distance_matrix

    last_route = load_route(ROUTE_FILE) if os.path.exists(ROUTE_FILE) else None
    x0 = [waypoint["station_id"] for waypoint in last_route] if last_route and len(last_route) == len(selected_stations) else None
    
    raw_route, _ = solve_tsp_simulated_annealing(selected_matrix, x0, alpha=0.97)
    route = format_python_tsp_route(selected_stations, raw_route)
    write_route_to_csv(route, ROUTE_FILE)
    create_map_w_directions(ROUTE_FILE)


if __name__ == "__main__":
    main()
