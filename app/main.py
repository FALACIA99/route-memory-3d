import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from app.models import (
    GenerateFromGpxRequest,
    GenerateFromLinkRequest,
    GenerateResponse,
)
from app.route_utils import (
    detect_platform,
    parse_gpx_content,
    compute_bbox,
    normalize_points_to_model,
)
from app.mesh_utils import export_combined_stl
from app.openapi_custom import custom_openapi
from app.link_resolvers import resolve_route_link_to_gpx, RouteLinkResolutionError


OUTPUT_DIR = "output"
PUBLIC_BASE_URL = "https://route-memory-3d.onrender.com"


app = FastAPI(
    title="Route Memory 3D API",
    version="1.0.0",
    description="Genera STL de rutas deportivas como recuerdo 3D."
)

app.openapi = lambda: custom_openapi(app)


@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Route Memory 3D API funcionando"
    }


@app.post("/generate-from-gpx", response_model=GenerateResponse)
def generate_from_gpx(payload: GenerateFromGpxRequest):
    try:
        raw_points = parse_gpx_content(payload.gpx_content)
        bbox = compute_bbox(raw_points, margin_percent=payload.bbox_margin_percent)

        normalized_points = normalize_points_to_model(
            points=raw_points,
            bbox=bbox,
            model_width_mm=payload.model_width_mm,
            model_height_mm=payload.model_height_mm,
            vertical_exaggeration=payload.vertical_exaggeration,
        )

        job_id = str(uuid.uuid4())
        filename = f"{job_id}.stl"
        output_path = os.path.join(OUTPUT_DIR, filename)

        export_combined_stl(
            route_points=normalized_points,
            model_width_mm=payload.model_width_mm,
            model_height_mm=payload.model_height_mm,
            base_thickness_mm=payload.base_thickness_mm,
            route_height_mm=payload.route_height_mm,
            output_path=output_path,
        )

        return GenerateResponse(
            success=True,
            message="STL generado correctamente desde GPX.",
            platform="gpx",
            route_name=payload.route_name,
            num_points=len(raw_points),
            bbox=bbox,
            stl_file=f"{PUBLIC_BASE_URL}/download/{filename}",
            note="Esta versión base crea una maqueta con base y ruta visible. Aún no reconstruye terreno DEM real."
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate-from-link", response_model=GenerateResponse)
def generate_from_link(payload: GenerateFromLinkRequest):
    platform = detect_platform(payload.route_url)

    try:
        gpx_content = resolve_route_link_to_gpx(payload.route_url)

        raw_points = parse_gpx_content(gpx_content)
        bbox = compute_bbox(raw_points, margin_percent=payload.bbox_margin_percent)

        normalized_points = normalize_points_to_model(
            points=raw_points,
            bbox=bbox,
            model_width_mm=payload.model_width_mm,
            model_height_mm=payload.model_height_mm,
            vertical_exaggeration=payload.vertical_exaggeration,
        )

        job_id = str(uuid.uuid4())
        filename = f"{job_id}.stl"
        output_path = os.path.join(OUTPUT_DIR, filename)

        export_combined_stl(
            route_points=normalized_points,
            model_width_mm=payload.model_width_mm,
            model_height_mm=payload.model_height_mm,
            base_thickness_mm=payload.base_thickness_mm,
            route_height_mm=payload.route_height_mm,
            output_path=output_path,
        )

        return GenerateResponse(
            success=True,
            message="STL generado correctamente desde link.",
            platform=platform,
            route_name=payload.route_name,
            num_points=len(raw_points),
            bbox=bbox,
            stl_file=f"{PUBLIC_BASE_URL}/download/{filename}",
            note="Link resuelto y convertido a ruta geográfica."
        )

    except RouteLinkResolutionError as e:
        return GenerateResponse(
            success=False,
            message="No se pudo extraer directamente la ruta desde el link.",
            platform=platform,
            route_name=payload.route_name,
            note=str(e)
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    return FileResponse(
        file_path,
        media_type="model/stl",
        filename=filename
    )