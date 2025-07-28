from python_tsp.heuristics import solve_tsp_simulated_annealing
from helpers import load_stations, get_haversine_distance_matrix, write_route_to_csv, create_interactive_map, format_python_tsp_route


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
    distance_matrix = get_haversine_distance_matrix(selected_stations)

    raw_route, _ = solve_tsp_simulated_annealing(distance_matrix)
    route = format_python_tsp_route(selected_stations, raw_route)
    write_route_to_csv(route, 'outputs/routes/haversine_route.csv')
    create_interactive_map(selected_stations, route, 'outputs/maps/haversine_map.html')


if __name__ == "__main__":
    main(5)
    