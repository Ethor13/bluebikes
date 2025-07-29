# cd into bike-osrm directory
cd bike-osrm

# Download map
# wget https://download.geofabrik.de/north-america/us/massachusetts-latest.osm.pbf

# Pull the OSRM Docker image
# docker pull osrm/osrm-backend

# Preprocess the map with bicycle routing profile
# docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-extract -p /opt/bicycle.lua /data/massachusetts-latest.osm.pbf

# docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-partition /data/massachusetts-latest.osrm
# docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-customize /data/massachusetts-latest.osrm

# Start the server
docker run -t -i -p 5000:5000 -v "${PWD}:/data" osrm/osrm-backend osrm-routed --algorithm mld /data/massachusetts-latest.osrm

cd ..