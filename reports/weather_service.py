"""
Real-time environmental weather feed for Bago City — Open-Meteo integration.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict

import requests
from django.utils import timezone

from myapp.models import Barangay, EnvironmentalData

logger = logging.getLogger(__name__)

BAGO_LATITUDE = 10.5383
BAGO_LONGITUDE = 122.8414
OPEN_METEO_URL = (
    'https://api.open-meteo.com/v1/forecast'
    f'?latitude={BAGO_LATITUDE}&longitude={BAGO_LONGITUDE}'
    '&current=temperature_2m,relative_humidity_2m,precipitation'
)
DATA_SOURCE = 'open-meteo-bago-city'
PERSIST_INTERVAL_MINUTES = 30

FALLBACK_WEATHER = {
    'temperature_c': 30.0,
    'humidity_pct': 70.0,
    'precipitation_mm': 0.0,
    'location': 'Bago City, Negros Occidental',
    'source': 'fallback',
    'ok': False,
    'vector_breeding_risk': False,
}


def _resolve_city_barangay() -> Barangay | None:
    """City-wide environmental readings are anchored to Poblacion when available."""
    return (
        Barangay.objects.filter(barangay_name__iexact='Poblacion').first()
        or Barangay.objects.order_by('id').first()
    )


def _build_payload(
    *,
    temperature_c: float,
    humidity_pct: float,
    precipitation_mm: float,
    ok: bool,
    source: str,
) -> Dict[str, Any]:
    return {
        'temperature_c': round(float(temperature_c), 1),
        'humidity_pct': round(float(humidity_pct), 1),
        'precipitation_mm': round(float(precipitation_mm), 2),
        'location': 'Bago City, Negros Occidental',
        'source': source,
        'ok': ok,
        'vector_breeding_risk': float(precipitation_mm) > 0,
        'fetched_at': timezone.now().isoformat(),
    }


def _should_persist_snapshot() -> bool:
    """Avoid writing a row on every dashboard refresh — keep ML training signal usable."""
    cutoff = timezone.now() - timedelta(minutes=PERSIST_INTERVAL_MINUTES)
    return not EnvironmentalData.objects.filter(
        data_source=DATA_SOURCE,
        recorded_at__gte=cutoff,
    ).exists()


def _save_environmental_snapshot(weather: Dict[str, Any]) -> None:
    barangay = _resolve_city_barangay()
    if not barangay:
        logger.warning('No barangay found — skipping environmental_data persistence.')
        return

    now = timezone.now()
    rainfall = weather['precipitation_mm']
    note_parts = [
        f'Open-Meteo snapshot for Bago City ({BAGO_LATITUDE}, {BAGO_LONGITUDE}).',
        f'Temperature {weather["temperature_c"]}°C, humidity {weather["humidity_pct"]}%.',
    ]
    if weather.get('vector_breeding_risk'):
        note_parts.append(
            'Elevated vector-breeding risk: active precipitation may expand mosquito habitat.'
        )

    try:
        EnvironmentalData.objects.create(
            barangay_id=barangay.id,
            data_source=DATA_SOURCE,
            temperature=Decimal(str(weather['temperature_c'])),
            humidity=Decimal(str(weather['humidity_pct'])),
            rainfall=Decimal(str(rainfall)),
            air_quality_index=None,
            recorded_at=now,
            risk_factor_note=' '.join(note_parts),
            created_at=now,
        )
    except Exception as exc:
        logger.exception('Failed to persist environmental weather snapshot: %s', exc)


def fetch_bago_city_weather(*, persist: bool = True) -> Dict[str, Any]:
    """
    Fetch live temperature, humidity, and rainfall for Bago City via Open-Meteo.

    Returns a structured dict safe for templates and ML feature pipelines.
    On API failure, returns conservative fallback defaults without raising.
    """
    try:
        response = requests.get(OPEN_METEO_URL, timeout=8)
        response.raise_for_status()
        payload = response.json()
        current = payload.get('current') or {}

        temperature = current.get('temperature_2m')
        humidity = current.get('relative_humidity_2m')
        precipitation = current.get('precipitation')

        if temperature is None or humidity is None or precipitation is None:
            raise ValueError('Open-Meteo response missing expected current weather fields.')

        weather = _build_payload(
            temperature_c=float(temperature),
            humidity_pct=float(humidity),
            precipitation_mm=float(precipitation),
            ok=True,
            source='open-meteo',
        )
    except Exception as exc:
        logger.warning('Weather fetch failed, using fallback values: %s', exc)
        weather = dict(FALLBACK_WEATHER)
        weather['fetched_at'] = timezone.now().isoformat()

    if persist and weather.get('ok') and _should_persist_snapshot():
        _save_environmental_snapshot(weather)

    return weather
