import gpxpy
from typing import List, Tuple, Dict


Point3D = Tuple[float, float, float]


def detect_platform(url: str) -> str:
    url_l = url.lower()
    if "strava" in url_l:
        return "strava"
    if "wikiloc" in url_l:
        return "wikiloc"
    if "garmin" in url_l:
        return "garmin"
    if "suunto" in url_l:
        return "suunto"
    if "komoot" in url_l:
        return "komoot"
    if "alltrails" in url_l:
        return "alltrails"
    return "unknown"


def parse_gpx_content(gpx_content: str) -> List[Point3D]:
    gpx = gpxpy.parse(gpx_content)
    points: List[Point3D] = []

    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                ele = p.elevation if p.elevation is not None else 0.0
                points.append((p.longitude, p.latitude, float(ele)))

    for route in gpx.routes:
        for p in route.points:
            ele = p.elevation if p.elevation is not None else 0.0
            points.append((p.longitude, p.latitude, float(ele)))

    if not points:
        raise ValueError("El GPX no contiene puntos de track ni route.")

    return points


def compute_bbox(points: List[Point3D], margin_percent: float = 15.0) -> Dict[str, float]:
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]

    min_lon = min(lons)
    max_lon = max(lons)
    min_lat = min(lats)
    max_lat = max(lats)

    lon_span = max_lon - min_lon
    lat_span = max_lat - min_lat

    if lon_span == 0:
        lon_span = 0.001
    if lat_span == 0:
        lat_span = 0.001

    lon_margin = lon_span * (margin_percent / 100.0)
    lat_margin = lat_span * (margin_percent / 100.0)

    return {
        "min_lon": min_lon - lon_margin,
        "max_lon": max_lon + lon_margin,
        "min_lat": min_lat - lat_margin,
        "max_lat": max_lat + lat_margin,
    }


def normalize_points_to_model(
    points: List[Point3D],
    bbox: Dict[str, float],
    model_width_mm: float,
    model_height_mm: float,
    vertical_exaggeration: float = 1.3,
    terrain_base_mm: float = 0.0,
) -> List[Tuple[float, float, float]]:
    min_lon = bbox["min_lon"]
    max_lon = bbox["max_lon"]
    min_lat = bbox["min_lat"]
    max_lat = bbox["max_lat"]

    lon_span = max_lon - min_lon
    lat_span = max_lat - min_lat

    elevations = [p[2] for p in points]
    min_ele = min(elevations)
    max_ele = max(elevations)
    ele_span = max(max_ele - min_ele, 1.0)

    normalized = []
    for lon, lat, ele in points:
        x = ((lon - min_lon) / lon_span) * model_width_mm
        y = ((lat - min_lat) / lat_span) * model_height_mm
        z = terrain_base_mm + (((ele - min_ele) / ele_span) * 20.0 * vertical_exaggeration)
        normalized.append((x, y, z))

    return normalized