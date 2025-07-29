import json
import requests
import folium
from typing import List, Dict, Tuple
from helpers import load_route

# OSRM settings
OSRM_URL = "http://localhost:5000/route/v1/bicycle"
ROUTE_FILE = 'outputs/routes/osrm_route.csv'
REQUEST_DELAY = 0.01  # Small delay between requests to avoid overwhelming the server

def get_route_geometry(start_coords: Tuple[float, float], end_coords: Tuple[float, float], retries: int = 3) -> Dict:
    """
    Get detailed route geometry from OSRM for a segment.
    
    Args:
        start_coords: (lng, lat) tuple for start point
        end_coords: (lng, lat) tuple for end point
        retries: Number of retry attempts
        
    Returns:
        Dictionary containing route information including geometry
    """
    start_lng, start_lat = start_coords
    end_lng, end_lat = end_coords
    
    # OSRM expects coordinates in lng,lat format
    url = f"{OSRM_URL}/{start_lng},{start_lat};{end_lng},{end_lat}"
    params = {
        'overview': 'full',  # Get full geometry
        'geometries': 'geojson',  # Return as GeoJSON
        'steps': 'true',  # Include turn-by-turn directions
        'annotations': 'true'  # Include additional route annotations
    }
    
    res = requests.get(url, params=params)
    res.raise_for_status()
    data = res.json()
    
    if data.get('code') == 'Ok' and data.get('routes'):
        route = data['routes'][0]
        return {
            'geometry': route['geometry'],
            'distance': route['distance'],  # in meters
            'duration': route['duration'],  # in seconds
            'legs': route.get('legs', []),
            'waypoints': data.get('waypoints', [])
        }
    else:
        print(f"OSRM error: {data.get('message', 'Unknown error')}")
        return None
    

def get_all_route_segments(route: List[Dict]) -> List[Dict]:
    """
    Get detailed routing information for all segments in the route.
    
    Args:
        route_data: List of station data from CSV
        
    Returns:
        List of route segments with detailed geometry
    """
    segments = []
    for i in range(len(route)):
        station = route[i]
        next_station = route[(i + 1) % len(route)]
        
        start_coords = (station['lng'], station['lat'])
        end_coords = (next_station['lng'], next_station['lat'])
        
        route_info = get_route_geometry(start_coords, end_coords)
        
        segments.append({
            'segment_id': i + 1,
            'from_station': station['station_name'],
            'to_station': next_station['station_name'],
            'from_coords': [station['lat'], station['lng']],
            'to_coords': [next_station['lat'], next_station['lng']],
            'distance_meters': route_info['distance'],
            'distance_km': route_info['distance'] / 1000,
            'duration_seconds': route_info['duration'],
            'duration_minutes': route_info['duration'] / 60,
            'geometry': route_info['geometry'],
            'legs': route_info['legs'],
            'waypoints': route_info['waypoints']
        })
    
    return segments

def create_geojson_output(route_data: List[Dict], segments: List[Dict]) -> Dict:
    """
    Create a GeoJSON FeatureCollection with the route and stations.
    
    Args:
        route_data: Original station data
        segments: Route segments with geometry
        
    Returns:
        GeoJSON FeatureCollection
    """
    features = []
    for station in route_data:
        point_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [station['lng'], station['lat']]
            },
            "properties": {
                "type": "station",
                "stop_number": station['stop_number'],
                "name": station['station_name'],
                "cumulative_distance_km": station['cumulative_distance_km']
            }
        }
        features.append(point_feature)
    
    # Add route segments
    for segment in segments:
        if segment['geometry']:  # Only add if we have actual geometry
            route_feature = {
                "type": "Feature",
                "geometry": segment['geometry'],
                "properties": {
                    "type": "route_segment",
                    "segment_id": segment['segment_id'],
                    "from_station": segment['from_station'],
                    "to_station": segment['to_station'],
                    "distance_km": segment['distance_km'],
                    "duration_minutes": segment['duration_minutes']
                }
            }
            features.append(route_feature)
    
    return {
        "type": "FeatureCollection",
        "features": features
    }

def create_folium_map_with_routes(route_data: List[Dict], segments: List[Dict], filename: str):
    """
    Create an interactive map with the actual routing paths.
    
    Args:
        route_data: Original station data
        segments: Route segments with geometry
        filename: Output HTML filename
    """
    # Calculate center point
    lats = [station['lat'] for station in route_data]
    lngs = [station['lng'] for station in route_data]
    center_lat = sum(lats) / len(lats)
    center_lng = sum(lngs) / len(lngs)
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Add station markers
    for station in route_data:
        popup_text = f"""
        <b>{station['station_name']}</b><br>
        Stop #{station['stop_number']}<br>
        Coordinates: {station['lat']:.6f}, {station['lng']:.6f}<br>
        Cumulative Distance: {station['cumulative_distance_km']:.2f} km
        """
        
        folium.Marker(
            location=[station['lat'], station['lng']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"Stop {station['stop_number']}: {station['station_name']}",
            icon=folium.Icon(color='blue', icon='bicycle', prefix='fa')
        ).add_to(m)
    
    # Add route segments
    total_segments_with_geometry = 0
    for segment in segments:
        if segment['geometry'] and segment['geometry']['coordinates']:
            # Convert GeoJSON coordinates to Folium format (lat, lng)
            coordinates = segment['geometry']['coordinates']
            if segment['geometry']['type'] == 'LineString':
                # Coordinates are in [lng, lat] format, need to flip to [lat, lng]
                route_coords = [[coord[1], coord[0]] for coord in coordinates]
                
                popup_text = f"""
                <b>Segment {segment['segment_id']}</b><br>
                From: {segment['from_station']}<br>
                To: {segment['to_station']}<br>
                Distance: {segment['distance_km']:.2f} km<br>
                Duration: {segment['duration_minutes']:.1f} minutes
                """
                
                folium.PolyLine(
                    locations=route_coords,
                    color='red',
                    weight=3,
                    opacity=0.8,
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=f"Segment {segment['segment_id']}"
                ).add_to(m)
                
                total_segments_with_geometry += 1
    
    # Add legend
    legend_html = f'''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
        <p><b>Blue Bikes TSP Route</b></p>
        <p><i class="fa fa-bicycle" style="color:blue"></i> Bike Station</p>
        <p><span style="color:red; font-weight:bold;">━━━</span> Bike Route</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save map
    m.save(filename)

def main(route_file):
    """Main function to process the route and get detailed directions."""
    route = load_route(route_file)

    route_file_stem = route_file.split('.')[0].split('/')[-1]

    segments = get_all_route_segments(route)
    with open(f'outputs/directions/{route_file_stem}_directions.json', 'w', encoding='utf-8') as file:
        json.dump(segments, file, indent=2, ensure_ascii=False)
    
    geojson_data = create_geojson_output(route, segments)
    with open(f'outputs/directions/{route_file_stem}_directions.geojson', 'w', encoding='utf-8') as file:
        json.dump(geojson_data, file, indent=2)
    create_folium_map_with_routes(route, segments, f'outputs/maps/{route_file_stem}_detailed.html')

if __name__ == "__main__":
    main(ROUTE_FILE)