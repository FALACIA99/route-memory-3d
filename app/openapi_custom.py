from fastapi.openapi.utils import get_openapi
import os


def custom_openapi(app):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Route Memory 3D API",
        version="2.0.0",
        summary="API para generar maquetas STL desde rutas deportivas",
        description=(
            "Recibe un link o GPX, extrae la ruta, calcula el área "
            "y genera un modelo STL imprimible con la ruta destacada."
        ),
        routes=app.routes,
    )

    server_url = os.getenv("OPENAPI_SERVER_URL", "http://127.0.0.1:8000")

    openapi_schema["servers"] = [
        {"url": server_url}
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema