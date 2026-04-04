class RouteLinkResolutionError(Exception):
    pass


def resolve_route_link_to_gpx(route_url: str) -> str:
    """
    Devuelve GPX como texto si logra resolver el link.
    Esta primera versión no hace scraping ni OAuth real.
    """

    url_l = route_url.lower()

    if "strava" in url_l:
        raise RouteLinkResolutionError(
            "Strava normalmente requiere integración específica u OAuth para exportar el track."
        )

    if "garmin" in url_l:
        raise RouteLinkResolutionError(
            "Garmin Connect normalmente requiere resolvedor específico u OAuth."
        )

    if "suunto" in url_l:
        raise RouteLinkResolutionError(
            "Suunto requiere integración específica."
        )

    if "wikiloc" in url_l:
        raise RouteLinkResolutionError(
            "Wikiloc puede requerir scraping controlado o exportación GPX del usuario."
        )

    raise RouteLinkResolutionError(
        "No se pudo resolver automáticamente el link. Solicita GPX/KML/FIT."
    )