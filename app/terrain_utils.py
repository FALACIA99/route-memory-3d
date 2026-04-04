import math
import time
from typing import Dict, List, Tuple

import numpy as np
import requests


Point3D = Tuple[float, float, float]
OPEN_TOPO_DATA_BASE_URL = "https://api.opentopodata.org/v1"
MAX_LOCATIONS_PER_REQUEST = 100
SECONDS_BETWEEN_REQUESTS = 1.05


def build_grid_coordinates(
    bbox: Dict[str, float],
    cols: int,
    rows: int,
) -> Tuple[np.ndarray, np.ndarray]:
    lons = np.linspace(bbox["min_lon"], bbox["max_lon"], cols)
    lats = np.linspace(bbox["min_lat"], bbox["max_lat"], rows)
    return lons, lats


def _chunk_locations(locations: List[str], chunk_size: int) -> List[List[str]]:
    return [locations[i:i + chunk_size] for i in range(0, len(locations), chunk_size)]


def fetch_elevation_grid(
    bbox: Dict[str, float],
    dataset: str = "srtm90m",
    cols: int = 30,
    rows: int = 30,
    timeout_seconds: int = 60,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    lons, lats = build_grid_coordinates(bbox, cols=cols, rows=rows)

    location_strings: List[str] = []
    for lat in lats:
        for lon in lons:
            location_strings.append(f"{lat:.8f},{lon:.8f}")

    chunks = _chunk_locations(location_strings, MAX_LOCATIONS_PER_REQUEST)
    elevations: List[float] = []

    for idx, chunk in enumerate(chunks):
        if idx > 0:
            time.sleep(SECONDS_BETWEEN_REQUESTS)

        locations_param = "|".join(chunk)
        url = f"{OPEN_TOPO_DATA_BASE_URL}/{dataset}"
        response = requests.get(
            url,
            params={"locations": locations_param},
            timeout=timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        if payload.get("status") != "OK":
            raise ValueError(f"Respuesta inválida de OpenTopoData: {payload}")

        results = payload.get("results", [])
        if len(results) != len(chunk):
            raise ValueError("La cantidad de elevaciones recibidas no coincide con la grilla solicitada.")

        for item in results:
            elevation = item.get("elevation")
            if elevation is None:
                elevations.append(np.nan)
            else:
                elevations.append(float(elevation))

    grid = np.array(elevations, dtype=float).reshape((rows, cols))
    grid = fill_nan_values(grid)

    return lons, lats, grid


def fill_nan_values(grid: np.ndarray) -> np.ndarray:
    if not np.isnan(grid).any():
        return grid

    filled = grid.copy()
    finite_values = filled[np.isfinite(filled)]
    if finite_values.size == 0:
        raise ValueError("No se obtuvieron elevaciones válidas para construir el terreno.")

    fallback = float(np.nanmean(finite_values))
    filled[np.isnan(filled)] = fallback
    return filled


def sample_grid_bilinear(
    grid: np.ndarray,
    x_ratio: float,
    y_ratio: float,
) -> float:
    rows, cols = grid.shape

    x = np.clip(x_ratio * (cols - 1), 0, cols - 1)
    y = np.clip(y_ratio * (rows - 1), 0, rows - 1)

    x0 = int(math.floor(x))
    x1 = min(x0 + 1, cols - 1)
    y0 = int(math.floor(y))
    y1 = min(y0 + 1, rows - 1)

    q11 = grid[y0, x0]
    q21 = grid[y0, x1]
    q12 = grid[y1, x0]
    q22 = grid[y1, x1]

    tx = x - x0
    ty = y - y0

    a = q11 * (1 - tx) + q21 * tx
    b = q12 * (1 - tx) + q22 * tx
    return float(a * (1 - ty) + b * ty)


def normalize_elevation_grid_to_mm(
    elevation_grid: np.ndarray,
    terrain_relief_mm: float,
    vertical_exaggeration: float,
) -> np.ndarray:
    min_ele = float(np.min(elevation_grid))
    max_ele = float(np.max(elevation_grid))
    span = max(max_ele - min_ele, 1.0)

    norm = (elevation_grid - min_ele) / span
    relief = terrain_relief_mm * vertical_exaggeration
    return norm * relief