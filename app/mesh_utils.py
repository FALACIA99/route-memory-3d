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

    for r in range(rows - 1):
        for c in range(cols - 1):
            v00 = top_index(r, c)
            v10 = top_index(r, c + 1)
            v01 = top_index(r + 1, c)
            v11 = top_index(r + 1, c + 1)

            faces.append([v00, v10, v11])
            faces.append([v00, v11, v01])

    for r in range(rows - 1):
        for c in range(cols - 1):
            v00 = bottom_index(r, c)
            v10 = bottom_index(r, c + 1)
            v01 = bottom_index(r + 1, c)
            v11 = bottom_index(r + 1, c + 1)

            faces.append([v00, v11, v10])
            faces.append([v00, v01, v11])

    r = 0
    for c in range(cols - 1):
        t0 = top_index(r, c)
        t1 = top_index(r, c + 1)
        b0 = bottom_index(r, c)
        b1 = bottom_index(r, c + 1)
        faces.append([b0, t1, t0])
        faces.append([b0, b1, t1])

    r = rows - 1
    for c in range(cols - 1):
        t0 = top_index(r, c)
        t1 = top_index(r, c + 1)
        b0 = bottom_index(r, c)
        b1 = bottom_index(r, c + 1)
        faces.append([b0, t0, t1])
        faces.append([b0, t1, b1])

    c = 0
    for r in range(rows - 1):
        t0 = top_index(r, c)
        t1 = top_index(r + 1, c)
        b0 = bottom_index(r, c)
        b1 = bottom_index(r + 1, c)
        faces.append([b0, t0, t1])
        faces.append([b0, t1, b1])

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


def rotation_matrix_from_vectors(vec1: np.ndarray, vec2: np.ndarray) -> np.ndarray:
    a = vec1 / np.linalg.norm(vec1)
    b = vec2 / np.linalg.norm(vec2)

    cross = np.cross(a, b)
    dot = np.dot(a, b)

    if np.isclose(dot, 1.0):
        return np.eye(4)

    if np.isclose(dot, -1.0):
        axis = np.array([1.0, 0.0, 0.0])
        if np.allclose(a, axis):
            axis = np.array([0.0, 1.0, 0.0])
        axis = axis / np.linalg.norm(axis)
        return trimesh.transformations.rotation_matrix(np.pi, axis)

    s = np.linalg.norm(cross)
    kmat = np.array([
        [0, -cross[2], cross[1]],
        [cross[2], 0, -cross[0]],
        [-cross[1], cross[0], 0]
    ])

    rotation_3x3 = np.eye(3) + kmat + kmat @ kmat * ((1 - dot) / (s ** 2))
    matrix = np.eye(4)
    matrix[:3, :3] = rotation_3x3
    return matrix


def route_centerline_offset(route_style: str, route_width_mm: float, route_height_mm: float) -> float:
    radius = route_width_mm / 2.0

    if route_style == "raised":
        return radius + (route_height_mm * 0.15)

    return (radius * 0.55) + (route_height_mm * 0.08)


def create_capsule_between_points(
    p1: Point3D,
    p2: Point3D,
    radius: float,
) -> trimesh.Trimesh:
    a = np.array(p1, dtype=float)
    b = np.array(p2, dtype=float)

    vec = b - a
    length = np.linalg.norm(vec)

    if length < 1e-6:
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=radius)
        sphere.apply_translation(a)
        return sphere

    cylinder_height = max(length - (2.0 * radius), 0.0)

    if cylinder_height <= 1e-6:
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=radius)
        sphere.apply_translation((a + b) / 2.0)
        return sphere

    capsule = trimesh.creation.capsule(height=cylinder_height, radius=radius, count=[16, 16])
    rot = rotation_matrix_from_vectors(np.array([0.0, 0.0, 1.0]), vec)
    capsule.apply_transform(rot)
    capsule.apply_translation((a + b) / 2.0)
    return capsule


def build_route_mesh_on_terrain(
    projected_route_points: List[Point3D],
    route_style: str,
    route_width_mm: float,
    route_height_mm: float,
) -> trimesh.Trimesh:
    if len(projected_route_points) < 2:
        raise ValueError("No hay suficientes puntos para construir la ruta sobre el terreno.")

    radius = route_width_mm / 2.0
    offset = route_centerline_offset(
        route_style=route_style,
        route_width_mm=route_width_mm,
        route_height_mm=route_height_mm,
    )

    centerline_points: List[Point3D] = []
    for x, y, z in projected_route_points:
        centerline_points.append((x, y, z + offset))

    meshes: List[trimesh.Trimesh] = []

    for i in range(len(centerline_points) - 1):
        seg = create_capsule_between_points(
            centerline_points[i],
            centerline_points[i + 1],
            radius=radius,
        )
        meshes.append(seg)

    for point in centerline_points:
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=radius * 0.98)
        sphere.apply_translation(point)
        meshes.append(sphere)

    return trimesh.util.concatenate(meshes)


def export_real_terrain_stl(
    route_points_geo: List[Point3D],
    bbox: Dict[str, float],
    elevation_mm_grid: np.ndarray,
    model_width_mm: float,
    model_height_mm: float,
    base_thickness_mm: float,
    route_style: str,
    route_width_mm: float,
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
        route_style=route_style,
        route_width_mm=route_width_mm,
        route_height_mm=route_height_mm,
    )

    combined = trimesh.util.concatenate([terrain_mesh, route_mesh])
    combined.export(output_path)

    return output_path