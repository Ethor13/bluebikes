import csv
import json
import requests
import time
from typing import List, Dict, Tuple

# OSRM settings
OSRM_URL = "http://localhost:5000/route/v1/bicycle"
REQUEST_DELAY = 0.01  # Small delay between requests to avoid overwhelming the server

def load_route_from_csv(filename: str) -> List[Dict]:
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
                'station_name': row['station_name'],
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'distance_to_next_km': float(row['distance_to_next_km']),
                'cumulative_distance_km': float(row['cumulative_distance_km'])
            })
    return route_data

def get_route_geometry(start_coords: Tuple[float, float], end_coords: Tuple[float, float], retries: int = 3) -> Dict:
    """
    Get detailed route geometry from OSRM for a segment.
    
    Args:
        start_coords: (longitude, latitude) tuple for start point
        end_coords: (longitude, latitude) tuple for end point
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
    
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
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
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(1)
        except Exception as e:
            print(f"Unexpected error (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(1)
    
    print(f"Failed to get route after {retries} attempts")
    return None

def get_all_route_segments(route_data: List[Dict]) -> List[Dict]:
    """
    Get detailed routing information for all segments in the route.
    
    Args:
        route_data: List of station data from CSV
        
    Returns:
        List of route segments with detailed geometry
    """
    segments = []
    
    print(f"Getting detailed routing for {len(route_data)} stations...")
    
    for i in range(len(route_data)):
        current_station = route_data[i]
        
        # Get next station (or loop back to first station for the last segment)
        if i < len(route_data) - 1:
            next_station = route_data[i + 1]
        else:
            # This is the return to start segment
            next_station = route_data[0]
        
        print(f"Processing segment {i + 1}/{len(route_data)}: {current_station['station_name']} → {next_station['station_name']}")
        
        # Get route geometry
        start_coords = (current_station['longitude'], current_station['latitude'])
        end_coords = (next_station['longitude'], next_station['latitude'])
        
        route_info = get_route_geometry(start_coords, end_coords)
        
        if route_info:
            segment = {
                'segment_id': i + 1,
                'from_station': current_station['station_name'],
                'to_station': next_station['station_name'],
                'from_coords': [current_station['latitude'], current_station['longitude']],
                'to_coords': [next_station['latitude'], next_station['longitude']],
                'distance_meters': route_info['distance'],
                'distance_km': route_info['distance'] / 1000,
                'duration_seconds': route_info['duration'],
                'duration_minutes': route_info['duration'] / 60,
                'geometry': route_info['geometry'],
                'legs': route_info['legs'],
                'waypoints': route_info['waypoints']
            }
            segments.append(segment)
        else:
            print(f"⚠️  Warning: Could not get routing for segment {i + 1}")
            # Fallback to straight line
            segments.append({
                'segment_id': i + 1,
                'from_station': current_station['station_name'],
                'to_station': next_station['station_name'],
                'from_coords': [current_station['latitude'], current_station['longitude']],
                'to_coords': [next_station['latitude'], next_station['longitude']],
                'distance_meters': current_station['distance_to_next_km'] * 1000,
                'distance_km': current_station['distance_to_next_km'],
                'duration_seconds': None,
                'duration_minutes': None,
                'geometry': None,  # No geometry available
                'legs': [],
                'waypoints': []
            })
        
        # Small delay to be nice to the OSRM server
        time.sleep(REQUEST_DELAY)
    
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
    
    # Add station points
    for station in route_data:
        point_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [station['longitude'], station['latitude']]
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

def save_enhanced_route_data(segments: List[Dict], filename: str = 'blue_bikes_detailed_route.json'):
    """
    Save the detailed route data as JSON.
    
    Args:
        segments: List of route segments
        filename: Output filename
    """
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(segments, file, indent=2, ensure_ascii=False)
    print(f"Detailed route data saved to '{filename}'")

def create_folium_map_with_routes(route_data: List[Dict], segments: List[Dict], filename: str = 'blue_bikes_route_detailed.html'):
    """
    Create an interactive map with the actual routing paths.
    
    Args:
        route_data: Original station data
        segments: Route segments with geometry
        filename: Output HTML filename
    """
    try:
        import folium
        from folium import plugins
    except ImportError:
        print("❌ Folium not available. Install with: pip install folium")
        return
    
    # Calculate center point
    lats = [station['latitude'] for station in route_data]
    lngs = [station['longitude'] for station in route_data]
    center_lat = sum(lats) / len(lats)
    center_lng = sum(lngs) / len(lngs)
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Add station markers
    for station in route_data:
        popup_text = f"""
        <b>{station['station_name']}</b><br>
        Stop #{station['stop_number']}<br>
        Coordinates: {station['latitude']:.6f}, {station['longitude']:.6f}<br>
        Cumulative Distance: {station['cumulative_distance_km']:.2f} km
        """
        
        folium.Marker(
            location=[station['latitude'], station['longitude']],
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
        <p><b>Stations:</b> {len(route_data)}</p>
        <p><b>Route Segments:</b> {total_segments_with_geometry}/{len(segments)}</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save map
    m.save(filename)
    print(f"Interactive map with detailed routes saved to '{filename}'")
    print(f"📍 Mapped {len(route_data)} stations with {total_segments_with_geometry} detailed route segments")

def main():
    """Main function to process the route and get detailed directions."""
    input_file = 'blue_bikes_route.csv'
    
    print("🚴 Blue Bikes Route Direction Generator")
    print("=" * 50)
    
    # Check if OSRM server is running
    try:
        response = requests.get(f"{OSRM_URL.replace('/route/v1/bicycle', '')}/", timeout=5)
        print("✅ OSRM server is running")
    except:
        print("❌ OSRM server not available at localhost:5000")
        print("   Please start the OSRM server with: ./init_osrm.sh")
        return
    
    # Load route data
    print(f"\n📄 Loading route data from '{input_file}'...")
    try:
        route_data = load_route_from_csv(input_file)
        print(f"✅ Loaded {len(route_data)} stations")
    except FileNotFoundError:
        print(f"❌ File '{input_file}' not found")
        return
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    # Get detailed routing for all segments
    print(f"\n🛣️  Getting detailed routing information...")
    segments = get_all_route_segments(route_data)
    
    successful_segments = sum(1 for seg in segments if seg['geometry'] is not None)
    print(f"✅ Successfully got routing for {successful_segments}/{len(segments)} segments")
    
    # Save detailed route data
    print(f"\n💾 Saving detailed route data...")
    save_enhanced_route_data(segments)
    
    # Create GeoJSON output
    geojson_data = create_geojson_output(route_data, segments)
    with open('blue_bikes_route.geojson', 'w', encoding='utf-8') as file:
        json.dump(geojson_data, file, indent=2)
    print("✅ GeoJSON saved to 'blue_bikes_route.geojson'")
    
    # Create interactive map
    print(f"\n🗺️  Creating interactive map...")
    create_folium_map_with_routes(route_data, segments)
    
    # Summary
    total_distance = sum(seg['distance_km'] for seg in segments if seg['distance_km'])
    total_duration = sum(seg['duration_minutes'] for seg in segments if seg['duration_minutes'])
    
    print(f"\n📊 Route Summary:")
    print(f"   • Total Stations: {len(route_data)}")
    print(f"   • Total Distance: {total_distance:.2f} km")
    if total_duration:
        print(f"   • Estimated Duration: {total_duration:.1f} minutes ({total_duration/60:.1f} hours)")
    print(f"   • Route Segments with Geometry: {successful_segments}/{len(segments)}")
    
    print(f"\n🎉 Route processing complete!")
    print(f"   Files generated:")
    print(f"   • blue_bikes_detailed_route.json (detailed route data)")
    print(f"   • blue_bikes_route.geojson (GeoJSON format)")
    print(f"   • blue_bikes_route_detailed.html (interactive map)")

if __name__ == "__main__":
    main()