import csv
import time
import requests
from tqdm import tqdm

# Settings
OSRM_URL = "http://localhost:5000/trip/v1/bicycle"
INPUT_FILE = "stations.csv"       # CSV with columns: id, station_name, lat, lng
OUTPUT_FILE = "waypoints.csv"

def load_stations(file_path):
    stations = []
    with open(file_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stations.append({
                "id": row["id"],
                "name": row["station_name"],
                "lat": float(row["lat"]),
                "lng": float(row["lng"])
            })
    return stations

def main(stations):
    url = f"{OSRM_URL}/{';'.join([f'{s['lng']},{s['lat']}' for s in stations])}"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()

    route = []
    if "waypoints" in data and data["waypoints"]:
        for idx, waypoint in enumerate(data["waypoints"]):
            station = stations[idx]
            route.append([
                waypoint["waypoint_index"],
                station["name"],
                station["lat"],
                station["lng"],
                waypoint["distance"]
            ])

    route.sort(key=lambda x: x[0])  # Sort by waypoint index

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['stop_number', 'station_name', 'latitude', 'longitude', 
                     'distance_to_next_km']
        writer = csv.writer(csvfile)
        
        writer.writerow(fieldnames)
        writer.writerows(route)

    return route


if __name__ == "__main__":
    stations = load_stations(INPUT_FILE)[:5]
    main(stations)