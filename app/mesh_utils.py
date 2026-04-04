import os
import math
import trimesh
from typing import List, Tuple


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