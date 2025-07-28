from python_tsp.heuristics import solve_tsp_simulated_annealing
from helpers import load_stations, create_interactive_map, load_distance_matrix, format_python_tsp_route, write_route_to_csv, create_interactive_map


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
    
    raw_route, _ = solve_tsp_simulated_annealing(selected_matrix, alpha=0.90)
    route = format_python_tsp_route(selected_stations, raw_route)
    write_route_to_csv(route, 'outputs/routes/shortest_distance_route.csv')
    create_interactive_map(selected_stations, route, 'outputs/maps/shortest_distance_map.html')


if __name__ == "__main__":
    main(5)
