from pydantic import BaseModel, Field
from typing import Optional, Literal


class GenerateFromLinkRequest(BaseModel):
    route_url: str = Field(..., description="Public or private route/activity URL")
    route_name: Optional[str] = Field(None, description="Optional user label for the route")
    model_width_mm: float = Field(180.0, ge=80, le=400)
    model_height_mm: float = Field(140.0, ge=80, le=400)
    base_thickness_mm: float = Field(8.0, ge=2, le=30)
    route_height_mm: float = Field(2.0, ge=0.5, le=10)
    bbox_margin_percent: float = Field(15.0, ge=0, le=100)
    vertical_exaggeration: float = Field(1.3, ge=0.1, le=10)
    output_format: Literal["stl"] = "stl"


class GenerateFromGpxRequest(BaseModel):
    gpx_content: str = Field(..., description="GPX content as raw XML text")
    route_name: Optional[str] = Field(None, description="Optional user label for the route")
    model_width_mm: float = Field(180.0, ge=80, le=400)
    model_height_mm: float = Field(140.0, ge=80, le=400)
    base_thickness_mm: float = Field(8.0, ge=2, le=30)
    route_height_mm: float = Field(2.0, ge=0.5, le=10)
    bbox_margin_percent: float = Field(15.0, ge=0, le=100)
    vertical_exaggeration: float = Field(1.3, ge=0.1, le=10)
    output_format: Literal["stl"] = "stl"


class GenerateFromGpxRealTerrainRequest(BaseModel):
    gpx_content: str = Field(..., description="GPX content as raw XML text")
    route_name: Optional[str] = Field(None, description="Optional user label for the route")
    model_width_mm: float = Field(180.0, ge=80, le=400)
    model_height_mm: float = Field(140.0, ge=80, le=400)
    base_thickness_mm: float = Field(8.0, ge=2, le=30)
    route_height_mm: float = Field(2.0, ge=0.5, le=10)
    bbox_margin_percent: float = Field(15.0, ge=0, le=100)
    vertical_exaggeration: float = Field(1.3, ge=0.1, le=10)
    terrain_dataset: Literal["srtm90m", "srtm30m", "aster30m", "mapzen"] = "srtm90m"
    terrain_grid_cols: int = Field(30, ge=10, le=60)
    terrain_grid_rows: int = Field(30, ge=10, le=60)
    terrain_relief_mm: float = Field(24.0, ge=5.0, le=80.0)
    output_format: Literal["stl"] = "stl"


class GenerateResponse(BaseModel):
    success: bool
    message: str
    platform: Optional[str] = None
    route_name: Optional[str] = None
    num_points: Optional[int] = None
    bbox: Optional[dict] = None
    stl_file: Optional[str] = None
    note: Optional[str] = None