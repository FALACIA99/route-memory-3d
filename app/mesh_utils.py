import os
import math
from typing import Dict, List, Tuple

import numpy as np
import trimesh

from app.terrain_utils import sample_grid_bilinear


Point3D = Tuple[float, float, float]


def create_base_plate(width_mm: float, height_mm: float, thickness_mm: float) -> trimesh.Trimesh:
    base = trimesh.creation.box(extents=(width_mm, height_mm, thickness_mm))
    base.apply_translation((width_mm / 2.0, height_mm / 2.0, thickness_mm / 2.0))
    return base


def create_route_segment_box(
    p1: Point3D,
    p2: Point3D,
    route_width_mm: float,
    route_height_mm: float,
    base_top_z: float,
) -> trimesh.Trimesh:
    x1, y1, z1 = p1
    x2, y2, z2 = p2

    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length < 0.01:
        length = 0.01

    box = trimesh.creation.box(extents=(length, route_width_mm, route_height_mm))

    angle = math.atan2(dy, dx)
    rot = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
    box.apply_transform(rot)

    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    cz = base_top_z + route_height_mm / 2.0 + max(z1, z2) * 0.05

    box.apply_translation((cx, cy, cz))
    return box


def build_route_mesh(
    route_points: List[Point3D],
    base_thickness_mm: float,
    route_width_mm: float = 2.2,
    route_height_mm: float = 2.0,
) -> trimesh.Trimesh:
    meshes = []
    base_top_z = base_thickness_mm

    for i in range(len(route_points) - 1):
        seg = create_route_segment_box(
            route_points[i],
            route_points[i + 1],
            route_width_mm=route_width_mm,
            route_height_mm=route_height_mm,
            base_top_z=base_top_z,
        )
        meshes.append(seg)

    if not meshes:
        raise ValueError("No se pudo generar la malla de la ruta.")

    return trimesh.util.concatenate(meshes)


def export_combined_stl(
    route_points: List[Point3D],
    model_width_mm: float,
    model_height_mm: float,
    base_thickness_mm: float,
    route_height_mm: float,
    output_path: str,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    base = create_base_plate(model_width_mm, model_height_mm, base_thickness_mm)
    route_mesh = build_route_mesh(
        route_points=route_points,
        base_thickness_mm=base_thickness_mm,
        route_width_mm=2.2,
        route_height_mm=route_height_mm,
    )

    combined = trimesh.util.concatenate([base, route_mesh])
    combined.export(output_path)

    return output_path


def build_terrain_solid_mesh(
    elevation_mm_grid: np.ndarray,
    width_mm: float,
    height_mm: float,
    base_thickness_mm: float,
) -> trimesh.Trimesh:
    rows, cols = elevation_mm_grid.shape
    xs = np.linspace(0.0, width_mm, cols)
    ys = np.linspace(0.0, height_mm, rows)

    top_vertices = []
    bottom_vertices = []

    for y_idx, y in enumerate(ys):
        for x_idx, x in enumerate(xs):
            z_top = base_thickness_mm + float(elevation_mm_grid[y_idx, x_idx])
            top_vertices.append([x, y, z_top])
            bottom_vertices.append([x, y, 0.0])

    vertices = np.array(top_vertices + bottom_vertices, dtype=float)
    top_offset = 0
    bottom_offset = rows * cols

    faces = []

    def top_index(r: int, c: int) -> int:
        return top_offset + (r * cols + c)

    def bottom_index(r: int, c: int) -> int:
        return bottom_offset + (r * cols + c)

    # Top faces
    for r in range(rows - 1):
        for c in range(cols - 1):
            v00 = top_index(r, c)
            v10 = top_index(r, c + 1)
            v01 = top_index(r + 1, c)
            v11 = top_index(r + 1, c + 1)

            faces.append([v00, v10, v11])
            faces.append([v00, v11, v01])

    # Bottom faces (reversed)
    for r in range(rows - 1):
        for c in range(cols - 1):
            v00 = bottom_index(r, c)
            v10 = bottom_index(r, c + 1)
            v01 = bottom_index(r + 1, c)
            v11 = bottom_index(r + 1, c + 1)

            faces.append([v00, v11, v10])
            faces.append([v00, v01, v11])

    # Side walls: top edge
    r = 0
    for c in range(cols - 1):
        t0 = top_index(r, c)
        t1 = top_index(r, c + 1)
        b0 = bottom_index(r, c)
        b1 = bottom_index(r, c + 1)
        faces.append([b0, t1, t0])
        faces.append([b0, b1, t1])

    # Side walls: bottom edge
    r = rows - 1
    for c in range(cols - 1):
        t0 = top_index(r, c)
        t1 = top_index(r, c + 1)
        b0 = bottom_index(r, c)
        b1 = bottom_index(r, c + 1)
        faces.append([b0, t0, t1])
        faces.append([b0, t1, b1])

    # Side walls: left edge
    c = 0
    for r in range(rows - 1):
        t0 = top_index(r, c)
        t1 = top_index(r + 1, c)
        b0 = bottom_index(r, c)
        b1 = bottom_index(r + 1, c)
        faces.append([b0, t0, t1])
        faces.append([b0, t1, b1])

    # Side walls: right edge
    c = cols - 1
    for r in range(rows - 1):
        t0 = top_index(r, c)
        t1 = top_index(r + 1, c)
        b0 = bottom_index(r, c)
        b1 = bottom_index(r + 1, c)
        faces.append([b0, t1, t0])
        faces.append([b0, b1, t1])

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.array(faces, dtype=int), process=True)
    return mesh


def project_route_points_onto_terrain(
    route_points_geo: List[Point3D],
    bbox: Dict[str, float],
    elevation_mm_grid: np.ndarray,
    model_width_mm: float,
    model_height_mm: float,
    base_thickness_mm: float,
) -> List[Point3D]:
    min_lon = bbox["min_lon"]
    max_lon = bbox["max_lon"]
    min_lat = bbox["min_lat"]
    max_lat = bbox["max_lat"]

    lon_span = max(max_lon - min_lon, 1e-9)
    lat_span = max(max_lat - min_lat, 1e-9)

    projected = []
    for lon, lat, _ in route_points_geo:
        x_ratio = (lon - min_lon) / lon_span
        y_ratio = (lat - min_lat) / lat_span

        x = x_ratio * model_width_mm
        y = y_ratio * model_height_mm
        z_relief = sample_grid_bilinear(elevation_mm_grid, x_ratio=x_ratio, y_ratio=y_ratio)
        z = base_thickness_mm + z_relief

        projected.append((x, y, z))

    return projected


def build_route_mesh_on_terrain(
    projected_route_points: List[Point3D],
    route_height_mm: float,
    route_width_mm: float = 2.2,
) -> trimesh.Trimesh:
    meshes = []

    for i in range(len(projected_route_points) - 1):
        x1, y1, z1 = projected_route_points[i]
        x2, y2, z2 = projected_route_points[i + 1]

        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.01:
            length = 0.01

        box = trimesh.creation.box(extents=(length, route_width_mm, route_height_mm))

        angle = math.atan2(dy, dx)
        rot = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
        box.apply_transform(rot)

        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        cz = max(z1, z2) + route_height_mm / 2.0

        box.apply_translation((cx, cy, cz))
        meshes.append(box)

    if not meshes:
        raise ValueError("No se pudo generar la ruta sobre el terreno.")

    return trimesh.util.concatenate(meshes)


def export_real_terrain_stl(
    route_points_geo: List[Point3D],
    bbox: Dict[str, float],
    elevation_mm_grid: np.ndarray,
    model_width_mm: float,
    model_height_mm: float,
    base_thickness_mm: float,
    route_height_mm: float,
    output_path: str,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    terrain_mesh = build_terrain_solid_mesh(
        elevation_mm_grid=elevation_mm_grid,
        width_mm=model_width_mm,
        height_mm=model_height_mm,
        base_thickness_mm=base_thickness_mm,
    )

    projected_route_points = project_route_points_onto_terrain(
        route_points_geo=route_points_geo,
        bbox=bbox,
        elevation_mm_grid=elevation_mm_grid,
        model_width_mm=model_width_mm,
        model_height_mm=model_height_mm,
        base_thickness_mm=base_thickness_mm,
    )

    route_mesh = build_route_mesh_on_terrain(
        projected_route_points=projected_route_points,
        route_height_mm=route_height_mm,
        route_width_mm=2.2,
    )

    combined = trimesh.util.concatenate([terrain_mesh, route_mesh])
    combined.export(output_path)

    return output_path