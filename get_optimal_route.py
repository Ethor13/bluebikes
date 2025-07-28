import json
import numpy as np
from python_tsp.exact import solve_tsp_dynamic_programming
from python_tsp.heuristics import solve_tsp_simulated_annealing
import folium
from folium import plugins
import csv

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

    # Sort stations by name
    parsed_stations.sort(key=lambda x: x[0])
    
    # Add incremental IDs and write to CSV
    csv_data = []
    for i, station in enumerate(parsed_stations):
        station_with_id = [i, station[0], station[1], station[2]]
        csv_data.append(station_with_id)
    
    # Write to CSV file
    with open('stations.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['id', 'station_name', 'lat', 'lng'])
        writer.writerows(csv_data)
    
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


def traveling_salesman_approximation(stations):
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
        # Use simulated annealing for larger datasets or if specified
        return solve_tsp_simulated_annealing(distance_matrix)
    
    except Exception as e:
        print(f"Error solving TSP: {e}")
        # Return a simple nearest neighbor fallback
        return list(range(len(stations))), np.sum(distance_matrix[0])


def export_tsp_route(stations, route, total_distance, filename='tsp_route.csv'):
    """
    Export the TSP route to a CSV file with detailed information.
    
    Args:
        stations (list): List of stations [name, lat, lng]
        route (list): List of station indices representing the route
        total_distance (float): Total distance of the route in kilometers
        filename (str): Output CSV filename
    """
    print(f"\nOptimal route ({total_distance:.2f} km total):")
    
    csv_data = []
    cumulative_distance = 0.0
    
    for i, station_idx in enumerate(route):
        station_name = stations[station_idx][0]
        lat = stations[station_idx][1]
        lng = stations[station_idx][2]
        
        # Calculate distance to next station
        if i < len(route) - 1:
            next_station_idx = route[i + 1]
            next_lat = stations[next_station_idx][1]
            next_lng = stations[next_station_idx][2]
            distance_to_next = haversine_distance(lat, lng, next_lat, next_lng)
        else:
            # Distance back to start station
            start_lat = stations[route[0]][1]
            start_lng = stations[route[0]][2]
            distance_to_next = haversine_distance(lat, lng, start_lat, start_lng)
        
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
    
    # Select subset if needed
    if max_stations is None or len(stations) < max_stations:
        selected_stations = stations
    else:
        selected_stations = stations[:max_stations]
        print(f"Using first {max_stations} stations for analysis")
    
    print(f"\nSolving TSP for {len(selected_stations)} stations...")
    
    route, total_distance = traveling_salesman_approximation(selected_stations)
    
    export_tsp_route(selected_stations, route, total_distance, 'blue_bikes_route.csv')
    
    if visualize:
        visualize_tsp_solution(selected_stations, route, total_distance)
    
    return selected_stations, route, total_distance


if __name__ == "__main__":
    stations = parse_stations("stations.json")
    
    # Run TSP analysis with visualization
    # You can adjust max_stations (up to ~20 for exact algorithm, more for approximation)
    selected_stations, route, total_distance = run_tsp_analysis(stations)
    
    print(f"\n🚴 Analysis complete! Optimized route covers {total_distance:.2f} km")
    print("Check the generated files:")
    print("- blue_bikes_route.csv (detailed route data)")
    print("- blue_bikes_tsp_route.html (interactive map)")
    
