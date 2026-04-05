import os
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from app.models import (
    GenerateFromGpxRequest,
    GenerateFromLinkRequest,
    GenerateFromGpxRealTerrainRequest,
    GenerateFromGpxBase64RealTerrainRequest,
    GenerateResponse,
)
from app.route_utils import (
    detect_platform,
    parse_gpx_content,
    compute_bbox,
    normalize_points_to_model,
)
from app.mesh_utils import (
    export_combined_stl,
    export_real_terrain_stl,
)
from app.terrain_utils import (
    fetch_elevation_grid,
    normalize_elevation_grid_to_mm,
)
from app.openapi_custom import custom_openapi
from app.link_resolvers import resolve_route_link_to_gpx, RouteLinkResolutionError
from app.file_utils import decode_uploaded_gpx, decode_gpx_base64


OUTPUT_DIR = "output"
PUBLIC_BASE_URL = "https://route-memory-3d.onrender.com"


app = FastAPI(
    title="Route Memory 3D API",
    version="5.0.0",
    description="Genera STL de rutas deportivas como recuerdo 3D."
)

app.openapi = lambda: custom_openapi(app)


def build_simple_stl_from_gpx_content(
    gpx_content: str,
    route_name: str | None,
    model_width_mm: float,
    model_height_mm: float,
    base_thickness_mm: float,
    route_height_mm: float,
    bbox_margin_percent: float,
    vertical_exaggeration: float,
) -> GenerateResponse:
    raw_points = parse_gpx_content(gpx_content)
    bbox = compute_bbox(raw_points, margin_percent=bbox_margin_percent)

    normalized_points = normalize_points_to_model(
        points=raw_points,
        bbox=bbox,
        model_width_mm=model_width_mm,
        model_height_mm=model_height_mm,
        vertical_exaggeration=vertical_exaggeration,
    )

    job_id = str(uuid.uuid4())
    filename = f"{job_id}.stl"
    output_path = os.path.join(OUTPUT_DIR, filename)

    export_combined_stl(
        route_points=normalized_points,
        model_width_mm=model_width_mm,
        model_height_mm=model_height_mm,
        base_thickness_mm=base_thickness_mm,
        route_height_mm=route_height_mm,
        output_path=output_path,
    )

    return GenerateResponse(
        success=True,
        message="STL generado correctamente desde GPX.",
        platform="gpx",
        route_name=route_name,
        num_points=len(raw_points),
        bbox=bbox,
        stl_file=f"{PUBLIC_BASE_URL}/download/{filename}",
        note="Versión simple con base y ruta visible."
    )


def build_real_terrain_stl_from_gpx_content(
    gpx_content: str,
    route_name: str | None,
    model_width_mm: float,
    model_height_mm: float,
    base_thickness_mm: float,
    route_style: str,
    route_width_mm: float,
    route_height_mm: float,
    bbox_margin_percent: float,
    vertical_exaggeration: float,
    terrain_dataset: str,
    terrain_grid_cols: int,
    terrain_grid_rows: int,
    terrain_relief_mm: float,
) -> GenerateResponse:
    raw_points = parse_gpx_content(gpx_content)
    bbox = compute_bbox(raw_points, margin_percent=bbox_margin_percent)

    _, _, elevation_grid = fetch_elevation_grid(
        bbox=bbox,
        dataset=terrain_dataset,
        cols=terrain_grid_cols,
        rows=terrain_grid_rows,
    )

    elevation_mm_grid = normalize_elevation_grid_to_mm(
        elevation_grid=elevation_grid,
        terrain_relief_mm=terrain_relief_mm,
        vertical_exaggeration=vertical_exaggeration,
    )

    job_id = str(uuid.uuid4())
    filename = f"{job_id}.stl"
    output_path = os.path.join(OUTPUT_DIR, filename)

    export_real_terrain_stl(
        route_points_geo=raw_points,
        bbox=bbox,
        elevation_mm_grid=elevation_mm_grid,
        model_width_mm=model_width_mm,
        model_height_mm=model_height_mm,
        base_thickness_mm=base_thickness_mm,
        route_style=route_style,
        route_width_mm=route_width_mm,
        route_height_mm=route_height_mm,
        output_path=output_path,
    )

    return GenerateResponse(
        success=True,
        message="STL generado correctamente desde GPX con topografía real.",
        platform=terrain_dataset,
        route_name=route_name,
        num_points=len(raw_points),
        bbox=bbox,
        stl_file=f"{PUBLIC_BASE_URL}/download/{filename}",
        note=(
            f"Topografía real con ruta estilo {route_style}, "
            f"ancho {route_width_mm} mm y grilla "
            f"{terrain_grid_cols}x{terrain_grid_rows}."
        ),
    )


@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Route Memory 3D API funcionando"
    }


@app.post("/generate-from-gpx", response_model=GenerateResponse)
def generate_from_gpx(payload: GenerateFromGpxRequest):
    try:
        return build_simple_stl_from_gpx_content(
            gpx_content=payload.gpx_content,
            route_name=payload.route_name,
            model_width_mm=payload.model_width_mm,
            model_height_mm=payload.model_height_mm,
            base_thickness_mm=payload.base_thickness_mm,
            route_height_mm=payload.route_height_mm,
            bbox_margin_percent=payload.bbox_margin_percent,
            vertical_exaggeration=payload.vertical_exaggeration,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate-from-gpx-file", response_model=GenerateResponse)
async def generate_from_gpx_file(
    gpx_file: UploadFile = File(...),
    route_name: str | None = Form(None),
    model_width_mm: float = Form(180.0),
    model_height_mm: float = Form(140.0),
    base_thickness_mm: float = Form(8.0),
    route_height_mm: float = Form(2.0),
    bbox_margin_percent: float = Form(15.0),
    vertical_exaggeration: float = Form(1.3),
):
    try:
        raw_bytes = await gpx_file.read()
        gpx_content = decode_uploaded_gpx(gpx_file, raw_bytes)

        return build_simple_stl_from_gpx_content(
            gpx_content=gpx_content,
            route_name=route_name or gpx_file.filename,
            model_width_mm=model_width_mm,
            model_height_mm=model_height_mm,
            base_thickness_mm=base_thickness_mm,
            route_height_mm=route_height_mm,
            bbox_margin_percent=bbox_margin_percent,
            vertical_exaggeration=vertical_exaggeration,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate-from-gpx-real-terrain", response_model=GenerateResponse)
def generate_from_gpx_real_terrain(payload: GenerateFromGpxRealTerrainRequest):
    try:
        return build_real_terrain_stl_from_gpx_content(
            gpx_content=payload.gpx_content,
            route_name=payload.route_name,
            model_width_mm=payload.model_width_mm,
            model_height_mm=payload.model_height_mm,
            base_thickness_mm=payload.base_thickness_mm,
            route_style=payload.route_style,
            route_width_mm=payload.route_width_mm,
            route_height_mm=payload.route_height_mm,
            bbox_margin_percent=payload.bbox_margin_percent,
            vertical_exaggeration=payload.vertical_exaggeration,
            terrain_dataset=payload.terrain_dataset,
            terrain_grid_cols=payload.terrain_grid_cols,
            terrain_grid_rows=payload.terrain_grid_rows,
            terrain_relief_mm=payload.terrain_relief_mm,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate-from-gpx-base64-real-terrain", response_model=GenerateResponse)
def generate_from_gpx_base64_real_terrain(payload: GenerateFromGpxBase64RealTerrainRequest):
    try:
        gpx_content = decode_gpx_base64(payload.gpx_base64)

        return build_real_terrain_stl_from_gpx_content(
            gpx_content=gpx_content,
            route_name=payload.route_name,
            model_width_mm=payload.model_width_mm,
            model_height_mm=payload.model_height_mm,
            base_thickness_mm=payload.base_thickness_mm,
            route_style=payload.route_style,
            route_width_mm=payload.route_width_mm,
            route_height_mm=payload.route_height_mm,
            bbox_margin_percent=payload.bbox_margin_percent,
            vertical_exaggeration=payload.vertical_exaggeration,
            terrain_dataset=payload.terrain_dataset,
            terrain_grid_cols=payload.terrain_grid_cols,
            terrain_grid_rows=payload.terrain_grid_rows,
            terrain_relief_mm=payload.terrain_relief_mm,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate-from-gpx-file-real-terrain", response_model=GenerateResponse)
async def generate_from_gpx_file_real_terrain(
    gpx_file: UploadFile = File(...),
    route_name: str | None = Form(None),
    model_width_mm: float = Form(180.0),
    model_height_mm: float = Form(140.0),
    base_thickness_mm: float = Form(8.0),
    route_style: str = Form("hybrid"),
    route_width_mm: float = Form(2.6),
    route_height_mm: float = Form(2.0),
    bbox_margin_percent: float = Form(15.0),
    vertical_exaggeration: float = Form(1.3),
    terrain_dataset: str = Form("srtm90m"),
    terrain_grid_cols: int = Form(30),
    terrain_grid_rows: int = Form(30),
    terrain_relief_mm: float = Form(24.0),
):
    try:
        if route_style not in {"raised", "hybrid"}:
            raise ValueError("route_style debe ser 'raised' o 'hybrid'")

        raw_bytes = await gpx_file.read()
        gpx_content = decode_uploaded_gpx(gpx_file, raw_bytes)

        return build_real_terrain_stl_from_gpx_content(
            gpx_content=gpx_content,
            route_name=route_name or gpx_file.filename,
            model_width_mm=model_width_mm,
            model_height_mm=model_height_mm,
            base_thickness_mm=base_thickness_mm,
            route_style=route_style,
            route_width_mm=route_width_mm,
            route_height_mm=route_height_mm,
            bbox_margin_percent=bbox_margin_percent,
            vertical_exaggeration=vertical_exaggeration,
            terrain_dataset=terrain_dataset,
            terrain_grid_cols=terrain_grid_cols,
            terrain_grid_rows=terrain_grid_rows,
            terrain_relief_mm=terrain_relief_mm,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate-from-link", response_model=GenerateResponse)
def generate_from_link(payload: GenerateFromLinkRequest):
    platform = detect_platform(payload.route_url)

    try:
        gpx_content = resolve_route_link_to_gpx(payload.route_url)

        return build_simple_stl_from_gpx_content(
            gpx_content=gpx_content,
            route_name=payload.route_name,
            model_width_mm=payload.model_width_mm,
            model_height_mm=payload.model_height_mm,
            base_thickness_mm=payload.base_thickness_mm,
            route_height_mm=payload.route_height_mm,
            bbox_margin_percent=payload.bbox_margin_percent,
            vertical_exaggeration=payload.vertical_exaggeration,
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