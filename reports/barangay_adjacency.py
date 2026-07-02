"""Adjacent barangay lookup for Bago City — derived from PSA boundary GeoJSON centroids."""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from django.conf import settings

GEOJSON_PATH = (
    Path(settings.BASE_DIR) / 'static' / 'ph-json' / 'bago_barangay_boundaries.geojson'
)
ADJACENCY_RADIUS_KM = 4.5

NAME_ALIASES = {
    'jorge l. araneta': 'Don Jorge Araneta',
    'jorgel.araneta': 'Don Jorge Araneta',
    'don jorge araneta': 'Don Jorge Araneta',
    'lag-asan': 'Lag-asan',
    'lag asan': 'Lag-asan',
    'ma-ao barrio': 'Ma-ao',
    'ma-aobarrio': 'Ma-ao',
    'ma-ao': 'Ma-ao',
}


def canonical_barangay_name(name: str) -> str:
    key = (name or '').strip().casefold()
    if not key:
        return ''
    return NAME_ALIASES.get(key, (name or '').strip())


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def _outer_ring(geometry: dict) -> list | None:
    geom_type = geometry.get('type')
    coords = geometry.get('coordinates')
    if not coords:
        return None
    if geom_type == 'Polygon':
        return coords[0]
    if geom_type == 'MultiPolygon':
        return coords[0][0]
    return None


def _polygon_centroid(geometry: dict) -> tuple[float, float]:
    ring = _outer_ring(geometry)
    if not ring:
        return 0.0, 0.0
    lats = [point[1] for point in ring]
    lons = [point[0] for point in ring]
    return sum(lats) / len(lats), sum(lons) / len(lons)


@lru_cache(maxsize=1)
def _load_barangay_geoindex() -> dict[str, tuple[str, tuple[float, float]]]:
    """
    Return ``{casefold_name: (display_name, (lat, lon))}`` from GeoJSON boundaries.
    """
    if not GEOJSON_PATH.is_file():
        return {}

    payload = json.loads(GEOJSON_PATH.read_text(encoding='utf-8'))
    index: dict[str, tuple[str, tuple[float, float]]] = {}
    for feature in payload.get('features', []):
        props = feature.get('properties') or {}
        raw_name = props.get('name') or props.get('psa_name') or ''
        display_name = canonical_barangay_name(raw_name)
        geometry = feature.get('geometry') or {}
        if not display_name or not geometry:
            continue
        index[display_name.casefold()] = (display_name, _polygon_centroid(geometry))
    return index


@lru_cache(maxsize=1)
def get_adjacency_map() -> dict[str, list[str]]:
    """Return ``{barangay_name: [neighbor_names...]}`` using centroid proximity."""
    geoindex = _load_barangay_geoindex()
    names = sorted((entry[0] for entry in geoindex.values()), key=str.casefold)
    adjacency: dict[str, list[str]] = {name: [] for name in names}

    for i, name_a in enumerate(names):
        _, (lat_a, lon_a) = geoindex[name_a.casefold()]
        for name_b in names[i + 1:]:
            _, (lat_b, lon_b) = geoindex[name_b.casefold()]
            if _haversine_km(lat_a, lon_a, lat_b, lon_b) <= ADJACENCY_RADIUS_KM:
                adjacency[name_a].append(name_b)
                adjacency[name_b].append(name_a)

    for name in adjacency:
        adjacency[name].sort(key=str.casefold)
    return adjacency


def get_neighboring_barangays(barangay_name: str) -> list[str]:
    """Return adjacent barangay names for ``barangay_name``, or ``[]`` if unknown."""
    canonical = canonical_barangay_name(barangay_name)
    if not canonical:
        return []

    neighbors = get_adjacency_map().get(canonical)
    if neighbors is not None:
        return neighbors

    geoindex = _load_barangay_geoindex()
    target = geoindex.get(canonical.casefold())
    if not target:
        return []

    _, (lat_a, lon_a) = target
    found: list[str] = []
    for display_name, (lat_b, lon_b) in geoindex.values():
        if display_name.casefold() == canonical.casefold():
            continue
        if _haversine_km(lat_a, lon_a, lat_b, lon_b) <= ADJACENCY_RADIUS_KM:
            found.append(display_name)
    return sorted(set(found), key=str.casefold)
