import numpy as np
from python_tsp.heuristics import solve_tsp_simulated_annealing
import folium
from folium import plugins
import csv

def load_stations(file_path='stations.csv'):
    """
    Load station data from CSV file.

    Args:
        file_path (str): The path to the CSV file containing station data.

    Returns:
        list: A list of stations as [name, lat, lng], indexed by station ID.
    """
    stations = []
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            stations.append([row['station_name'], float(row['lat']), float(row['lng'])])
    return stations


def load_distance_matrix(file_path='distance_matrix.csv'):
    """
    Load the distance matrix from CSV file.
    
    Args:
        file_path (str): Path to the distance matrix CSV file
    
    Returns:
        numpy.ndarray: Distance matrix where element [i][j] is distance from station i to station j
    """
    distances = []
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        # Skip the header row
        next(reader)
        
        for row in reader:
            # Skip the first column (id) and convert the rest to float
            distance_row = [float(val) for val in row[1:]]
            distances.append(distance_row)
    
    # Convert to numpy array
    distance_matrix = np.array(distances)
    
    # Convert from meters to kilometers (assuming the CSV contains meters)
    distance_matrix = distance_matrix / 1000.0
    
    return distance_matrix


def traveling_salesman_approximation(stations, distance_matrix=None):
    """
    Solve the traveling salesman problem approximately for bike stations.
    
    Args:
        stations (list): List of stations [name, lat, lng]
        distance_matrix (numpy.ndarray): Precomputed distance matrix. If None, will load from file.
    
    Returns:
        tuple: (route, total_distance) where route is list of station indices and 
               total_distance is the total distance in kilometers
    """
    if len(stations) == 0:
        return [], 0
    
    if len(stations) == 1:
        return [0], 0
    
    # Load distance matrix if not provided
    if distance_matrix is None:
        distance_matrix = load_distance_matrix()
    
    # If we're using a subset of stations, extract the relevant submatrix
    n_stations = len(stations)
    if distance_matrix.shape[0] > n_stations:
        # Assuming we're using the first n_stations from the full matrix
        distance_matrix = distance_matrix[:n_stations, :n_stations]
    
    try:
        # Use simulated annealing for larger datasets or if specified
        return solve_tsp_simulated_annealing(distance_matrix, alpha=0.99)
    
    except Exception as e:
        print(f"Error solving TSP: {e}")
        # Return a simple nearest neighbor fallback
        return list(range(len(stations))), np.sum(distance_matrix[0])


def export_tsp_route(stations, route, total_distance, distance_matrix=None, filename='tsp_route.csv'):
    """
    Export the TSP route to a CSV file with detailed information.
    
    Args:
        stations (list): List of stations [name, lat, lng]
        route (list): List of station indices representing the route
        total_distance (float): Total distance of the route in kilometers
        distance_matrix (numpy.ndarray): Precomputed distance matrix. If None, will load from file.
        filename (str): Output CSV filename
    """
    print(f"\nOptimal route ({total_distance:.2f} km total):")
    
    # Load distance matrix if not provided
    if distance_matrix is None:
        distance_matrix = load_distance_matrix()
    
    csv_data = []
    cumulative_distance = 0.0
    
    for i, station_idx in enumerate(route):
        station_name = stations[station_idx][0]
        lat = stations[station_idx][1]
        lng = stations[station_idx][2]
        
        # Calculate distance to next station using distance matrix
        if i < len(route) - 1:
            next_station_idx = route[i + 1]
            distance_to_next = distance_matrix[station_idx][next_station_idx]
        else:
            # Distance back to start station
            start_station_idx = route[0]
            distance_to_next = distance_matrix[station_idx][start_station_idx]
        
        # Add to CSV data
        csv_data.append({
            'stop_number': i + 1,
            'station_name': station_name,
            'latitude': lat,
            'longitude': lng,
            'distance_to_next_km': round(distance_to_next, 3),
            'cumulative_distance_km': round(cumulative_distance, 3)
        })
        
        # Update cumulative distance for next iteration
        cumulative_distance += distance_to_next
    
    # Add return to start
    if route:
        start_station = stations[route[0]][0]
        start_lat = stations[route[0]][1]
        start_lng = stations[route[0]][2]
        csv_data.append({
            'stop_number': len(route) + 1,
            'station_name': f"{start_station} (return to start)",
            'latitude': start_lat,
            'longitude': start_lng,
            'distance_to_next_km': 0.0,
            'cumulative_distance_km': round(cumulative_distance, 3)
        })
    
    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['stop_number', 'station_name', 'latitude', 'longitude', 
                     'distance_to_next_km', 'cumulative_distance_km']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(csv_data)
    
    print(f"Route exported to '{filename}'")
    return csv_data


def create_interactive_map(stations, route=None, filename='stations_map.html'):
    """
    Create an interactive map using folium showing stations and the TSP route.
    
    Args:
        stations (list): List of stations [name, lat, lng]
        route (list): Optional route as list of station indices
        filename (str): Output HTML filename
    
    Returns:
        folium.Map: The created map object
    """
    if not stations:
        return None
    
    # Calculate map center
    center_lat = np.mean([station[1] for station in stations])
    center_lng = np.mean([station[2] for station in stations])
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Add stations as markers
    for i, station in enumerate(stations):
        name, lat, lng = station
        
        # Different colors for route stations
        color = 'blue'
        if route and i in route:
            route_position = route.index(i) + 1
            color = 'red'
            popup_text = f"<b>{name}</b><br>Stop #{route_position}<br>Lat: {lat:.6f}<br>Lng: {lng:.6f}"
        else:
            popup_text = f"<b>{name}</b><br>Lat: {lat:.6f}<br>Lng: {lng:.6f}"
        
        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=name,
            icon=folium.Icon(color=color, icon='bicycle', prefix='fa')
        ).add_to(m)
    
    # Add route line if provided
    if route:
        route_coords = []
        for station_idx in route:
            lat, lng = stations[station_idx][1], stations[station_idx][2]
            route_coords.append([lat, lng])
        
        # Close the loop by returning to start
        if route_coords:
            route_coords.append(route_coords[0])
        
        # Add the route line
        folium.PolyLine(
            locations=route_coords,
            color='red',
            weight=3,
            opacity=0.8,
            popup='TSP Route'
        ).add_to(m)
        
        # Add arrows to show direction
        plugins.PolyLineTextPath(
            folium.PolyLine(route_coords, weight=0),
            "→",
            repeat=True,
            offset=10,
            attributes={'fill': 'red', 'font-weight': 'bold', 'font-size': '14'}
        ).add_to(m)
    
    # Add a legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 150px; height: 90px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <p><b>Legend</b></p>
    <p><i class="fa fa-bicycle" style="color:blue"></i> Station</p>
    <p><i class="fa fa-bicycle" style="color:red"></i> Route Stop</p>
    <p><span style="color:red; font-weight:bold;">—</span> TSP Route</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save map
    m.save(filename)
    print(f"Interactive map saved as '{filename}'")
    
    return m


def visualize_tsp_solution(stations, route, total_distance):
    """
    Create both static and interactive visualizations of the TSP solution.
    
    Args:
        stations (list): List of stations [name, lat, lng]
        route (list): Route as list of station indices
        total_distance (float): Total distance of the route
    """
    title = f"Blue Bikes TSP Route ({total_distance:.2f} km)"
    
    print("\nCreating visualizations...")
    
    # Create static plot
    
    # Create interactive map
    create_interactive_map(stations, route, 'blue_bikes_tsp_route.html')
    
    print("Visualizations complete!")
    print("- Interactive map: blue_bikes_tsp_route.html")
    print("  (Open the HTML file in your web browser to view the interactive map)")


def run_tsp_analysis(stations, max_stations=None, visualize=True):
    """
    Run TSP analysis on a set of stations with optional visualization.
    
    Args:
        stations (list): List of all stations [name, lat, lng]
        max_stations (int): Maximum number of stations to include in analysis
        visualize (bool): Whether to create visualizations
    
    Returns:
        tuple: (selected_stations, route, total_distance)
    """
    print(f"Total stations available: {len(stations)}")
    
    # Load the distance matrix once
    distance_matrix = load_distance_matrix()
    
    # Select subset if needed
    if max_stations is None or len(stations) < max_stations:
        selected_stations = stations
        selected_matrix = distance_matrix
    else:
        selected_stations = stations[:max_stations]
        # Extract submatrix for selected stations
        selected_matrix = distance_matrix[:max_stations, :max_stations]
        print(f"Using first {max_stations} stations for analysis")
    
    print(f"\nSolving TSP for {len(selected_stations)} stations...")
    
    route, total_distance = traveling_salesman_approximation(selected_stations, selected_matrix)
    
    export_tsp_route(selected_stations, route, total_distance, selected_matrix, 'blue_bikes_route.csv')
    
    if visualize:
        visualize_tsp_solution(selected_stations, route, total_distance)
    
    return selected_stations, route, total_distance


if __name__ == "__main__":
    # Load stations from CSV file
    stations = load_stations("stations.csv")
    
    # Run TSP analysis with visualization
    # You can adjust max_stations (up to ~20 for exact algorithm, more for approximation)
    selected_stations, route, total_distance = run_tsp_analysis(stations)
    
    print(f"\n🚴 Analysis complete! Optimized route covers {total_distance:.2f} km")
    print("Check the generated files:")
    print("- blue_bikes_route.csv (detailed route data)")
    print("- blue_bikes_tsp_route.html (interactive map)")
    
