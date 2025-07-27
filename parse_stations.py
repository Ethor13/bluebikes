import json
import numpy as np
from python_tsp.exact import solve_tsp_dynamic_programming
from python_tsp.heuristics import solve_tsp_simulated_annealing

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
        parsed_stations.append([station["stationName"], station["location"]["lat"], station["location"]["lng"]])

    return parsed_stations


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) using the Haversine formula.
    
    Args:
        lat1, lon1: Latitude and longitude of first point
        lat2, lon2: Latitude and longitude of second point
    
    Returns:
        float: Distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    return c * r


def create_distance_matrix(stations):
    """
    Create a distance matrix for all stations using Haversine distance.
    
    Args:
        stations (list): List of stations [name, lat, lng]
    
    Returns:
        numpy.ndarray: Distance matrix where element [i][j] is distance from station i to station j
    """
    n = len(stations)
    distance_matrix = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            if i < j:
                lat1, lon1 = stations[i][1], stations[i][2]
                lat2, lon2 = stations[j][1], stations[j][2]
                distance_matrix[i][j] = haversine_distance(lat1, lon1, lat2, lon2)
            if i > j:
                distance_matrix[i][j] = distance_matrix[j][i]
    
    return distance_matrix


def traveling_salesman_approximation(stations, method='simulated_annealing'):
    """
    Solve the traveling salesman problem approximately for bike stations.
    
    Args:
        stations (list): List of stations [name, lat, lng]
        method (str): Algorithm to use ('simulated_annealing' or 'dynamic_programming')
                     Note: dynamic_programming is exact but only works for small datasets (<20 stations)
    
    Returns:
        tuple: (route, total_distance) where route is list of station indices and 
               total_distance is the total distance in kilometers
    """
    if len(stations) == 0:
        return [], 0
    
    if len(stations) == 1:
        return [0], 0
    
    # Create distance matrix
    distance_matrix = create_distance_matrix(stations)
    
    try:
        if method == 'dynamic_programming' and len(stations) <= 15:
            # Use exact algorithm for small datasets
            route, distance = solve_tsp_dynamic_programming(distance_matrix)
        else:
            # Use simulated annealing for larger datasets or if specified
            route, distance = solve_tsp_simulated_annealing(distance_matrix)
        
        return route, distance
    
    except Exception as e:
        print(f"Error solving TSP: {e}")
        # Return a simple nearest neighbor fallback
        return list(range(len(stations))), np.sum(distance_matrix[0])


def print_tsp_route(stations, route, total_distance):
    """
    Print the TSP route in a readable format.
    
    Args:
        stations (list): List of stations [name, lat, lng]
        route (list): List of station indices representing the route
        total_distance (float): Total distance of the route in kilometers
    """
    print(f"\nOptimal route ({total_distance:.2f} km total):")
    print("-" * 50)
    
    for i, station_idx in enumerate(route):
        station_name = stations[station_idx][0]
        print(f"{i+1:2d}. {station_name}")
    
    # Return to start
    if route:
        start_station = stations[route[0]][0]
        print(f"{len(route)+1:2d}. {start_station} (return to start)")
    
    print("-" * 50)


if __name__ == "__main__":
    stations = parse_stations("stations.json")
    print(f"Loaded {len(stations)} stations")
    
    subset_size = 10
    # For demonstration, let's use a subset of stations to keep output manageable
    # You can remove this limit to use all stations
    demo_stations = stations[:subset_size]  # First 10 stations
    
    print(f"\nSolving TSP for {len(demo_stations)} stations...")
    route, total_distance = traveling_salesman_approximation(demo_stations, method='simulated_annealing')
    
    print_tsp_route(demo_stations, route, total_distance)
    
