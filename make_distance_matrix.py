import csv
import time
import requests
from tqdm import tqdm

# Settings
OSRM_URL = "http://localhost:5000/route/v1/bicycle"
INPUT_FILE = "stations.csv"       # CSV with columns: id, station_name, lat, lng
METRIC = "distance"
OUTPUT_FILE = f"{METRIC}_matrix.csv"
REQUEST_DELAY = 0.005               # Delay between requests (5ms)

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


def query_route(o_lng, o_lat, d_lng, d_lat, retries=3):
    url = f"{OSRM_URL}/{o_lng},{o_lat};{d_lng},{d_lat}?overview=false"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            data = r.json()
            if "routes" in data and data["routes"]:
                route = data["routes"][0]
                return route[METRIC]
        except Exception as e:
            print(f"Error on attempt {attempt+1} for {url}: {e}")
            time.sleep(1)
    return None


def build_and_write_matrix(file_path, stations):
    n = len(stations)
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["id"] + [s["id"] for s in stations]
        writer.writerow(header)

        for i in tqdm(range(n), desc="Building matrix", unit="row"):
            row = [0.0] * n
            for j in range(n):
                if i == j:
                    continue
                dist = query_route(stations[i]["lng"], stations[i]["lat"], stations[j]["lng"], stations[j]["lat"])
                row[j] = dist
                time.sleep(REQUEST_DELAY)
            writer.writerow([stations[i]["id"]] + row)
            f.flush()  # Ensure it's written to disk immediately to free memory


def main():
    stations = load_stations(INPUT_FILE)
    build_and_write_matrix(OUTPUT_FILE, stations)
    print(f"{METRIC} matrix saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
