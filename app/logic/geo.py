from math import radians, sin, cos, sqrt, asin, atan2, degrees

EARTH_RADIUS_M = 6371000

# https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points

def haversine_distance_m(lat1, lon1, lat2, lon2):
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return EARTH_RADIUS_M * c


# convert lat/lon to local X/Y meters relative to origin
# X = east, Y = north

def latlon_to_local_xy_m(origin_lat, origin_lon, target_lat, target_lon):
    origin_lat_rad = radians(origin_lat)
    origin_lon_rad = radians(origin_lon)
    target_lat_rad = radians(target_lat)
    target_lon_rad = radians(target_lon)

    dlat = target_lat_rad - origin_lat_rad
    dlon = target_lon_rad - origin_lon_rad

    x = EARTH_RADIUS_M * dlon * cos((origin_lat_rad + target_lat_rad) / 2)
    y = EARTH_RADIUS_M * dlat

    return x, y


def destination_point(lat, lon, bearing_deg, distance_m):
    if distance_m == 0:
        return lat, lon
    
    bearing_rad = radians(bearing_deg % 360)
    lat_rad = radians(lat)
    lon_rad = radians(lon)

    angular_distance = distance_m / EARTH_RADIUS_M

    # AI
    dest_lat_rad = asin(sin(lat_rad) * cos(angular_distance) + cos(lat_rad) * sin(angular_distance) * cos(bearing_rad))
    dest_lon_rad = lon_rad + atan2(
        sin(bearing_rad) * sin(angular_distance) * cos(lat_rad),
        cos(angular_distance) - sin(lat_rad) * sin(dest_lat_rad)
    )

    return degrees(dest_lat_rad), degrees(dest_lon_rad)