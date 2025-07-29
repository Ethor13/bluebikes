import csv
import numpy as np
import folium
from folium import plugins

def load_stations():
    stations = []
    with open("data/stations/stations.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stations.append({
                "id": row["id"],
                "station_name": row["station_name"],
                "lat": float(row["lat"]),
                "lng": float(row["lng"])
            })
    return stations

def write_route_to_csv(route, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['stop_number', 'station_id', 'station_name', 'lat', 'lng', 'distance_to_next_km', 'cumulative_distance_km']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(route)

    print(f"Route written to {output_file}. Total Distance: {route[-1]['cumulative_distance_km']} km")

def load_route(filename: str):
    """
    Load the route data from the CSV file.
    
    Returns:
        List of dictionaries with station data
    """
    route_data = []
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            route_data.append({
                'stop_number': int(row['stop_number']),
                'station_id': int(row['station_id']),
                'station_name': row['station_name'],
                'lat': float(row['lat']),
                'lng': float(row['lng']),
                'distance_to_next_km': float(row['distance_to_next_km']),
                'cumulative_distance_km': float(row['cumulative_distance_km'])
            })
    return route_data

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

def get_haversine_distance_matrix(stations):
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
                lat1, lon1 = stations[i]["lat"], stations[i]["lng"]
                lat2, lon2 = stations[j]["lat"], stations[j]["lng"]
                distance_matrix[i][j] = haversine_distance(lat1, lon1, lat2, lon2)
            if i > j:
                distance_matrix[i][j] = distance_matrix[j][i]
    
    return distance_matrix

def load_distance_matrix(metric):
    """
    Load the distance matrix from CSV file.
    
    Args:
        file_path (str): Path to the distance matrix CSV file
    
    Returns:
        numpy.ndarray: Distance matrix where element [i][j] is distance from station i to station j
    """
    file_path = 'data/stations/distance_matrix.csv' if metric == "distance" else 'data/stations/duration_matrix.csv'
    distances = []
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        
        for row in reader:
            distance_row = [float(val) for val in row[1:]]
            distances.append(distance_row)
    
    return np.array(distances) / 1000.0

def format_python_tsp_route(stations, route):
    """
    Export the TSP route to a CSV file with detailed information.
    
    Args:
        stations (list): List of stations [name, lat, lng]
        route (list): List of station indices representing the route
        total_distance (float): Total distance of the route in kilometers
        filename (str): Output CSV filename
    """
    csv_data = []
    cumulative_distance = 0.0
    
    for i, station_idx in enumerate(route):
        station = stations[station_idx]
        
        # Calculate distance to next station
        if i < len(route) - 1:
            next_station = stations[route[i + 1]]
            distance_to_next = haversine_distance(station["lat"], station["lng"], next_station["lat"], next_station["lng"])
        else:
            distance_to_next = 0
        
        # Add to CSV data
        csv_data.append({
            "stop_number": i + 1,
            "station_id": station["id"],
            "station_name": station["station_name"],
            "lat": station["lat"],
            "lng": station["lng"],
            "distance_to_next_km": round(distance_to_next, 3),
            "cumulative_distance_km": round(cumulative_distance, 3)
        })
        
        # Update cumulative distance for next iteration
        cumulative_distance += distance_to_next
    
    return csv_data


def create_interactive_map(stations, route, filename):
    """
    Create an interactive map using folium showing stations and the TSP route.
    
    Args:
        stations (list): List of stations [name, lat, lng]
        route (list): Optional route as list of station indices
        filename (str): Output HTML filename
    
    Returns:
        folium.Map: The created map object
    """
    # Calculate map center
    center_lat = np.mean([s["lat"] for s in stations])
    center_lng = np.mean([s["lng"] for s in stations])
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Add stations as markers
    for i, station in enumerate(stations):
        station_name, lat, lng = station["station_name"], station["lat"], station["lng"]
        
        # Different colors for route stations
        color = 'blue'
        if route and i in route:
            route_position = route.index(i) + 1
            color = 'red'
            popup_text = f"<b>{station_name}</b><br>Stop #{route_position}<br>Lat: {lat:.6f}<br>Lng: {lng:.6f}"
        else:
            popup_text = f"<b>{station_name}</b><br>Lat: {lat:.6f}<br>Lng: {lng:.6f}"
        
        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=station_name,
            icon=folium.Icon(color=color, icon='bicycle', prefix='fa')
        ).add_to(m)
    
    # Add route line if provided
    if route:
        route_coords = []
        for waypoint in route:
            lat, lng = waypoint["lat"], waypoint["lng"]
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
    
    return m