"""
YatraPilot AI — MapTiler Cloud Service Integration
Provides geocoding, interactive route computation, transit hub markers,
and map visualization config using MapTiler Cloud APIs with OpenStreetMap & Nominatim fallback.
Website: https://cloud.maptiler.com/
"""

import os
import math
import logging
import requests
from typing import Dict, List, Optional, Tuple, Any
from .base import RouteSummary
from .nominatim import nominatim_service

logger = logging.getLogger(__name__)

MAPTILER_GEOCODING_URL = "https://api.maptiler.com/geocoding"
MAPTILER_ROUTING_URL = "https://api.maptiler.com/routing/v2"
MAPTILER_MAP_STYLE = "https://api.maptiler.com/maps/streets-v2/style.json"
USER_AGENT = "YatraPilot-AI/1.0 (travel-planner; support@yatrapilot.ai)"


class MapTilerService:
    """MapTiler Cloud integration with seamless Leaflet & OpenStreetMap fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.getenv("MAPTILER_API_KEY", "")).strip()
        self.is_configured = bool(self.api_key and len(self.api_key) > 5 and self.api_key != "get_your_key_at_maptiler")
        self._key_tested = False
        self._key_valid = False

    def _test_key(self) -> bool:
        """Pings MapTiler tile endpoint once to verify key authorization."""
        if not self.is_configured:
            return False
        if self._key_tested:
            return self._key_valid

        try:
            url = f"https://api.maptiler.com/maps/streets-v2/0/0/0.png?key={self.api_key}"
            resp = requests.head(url, headers={"User-Agent": USER_AGENT}, timeout=4)
            self._key_tested = True
            self._key_valid = (resp.status_code == 200)
            if not self._key_valid:
                logger.info(f"MapTiler key returned HTTP {resp.status_code}. Seamlessly falling back to OpenStreetMap.")
            return self._key_valid
        except Exception:
            self._key_tested = True
            self._key_valid = False
            return False

    def get_map_config(self) -> Dict[str, Any]:
        """
        Returns frontend configuration for interactive maps.
        If MapTiler key is authorized, uses MapTiler.
        Otherwise, falls back to OpenStreetMap per requirement.
        """
        if self.is_configured and self._test_key():
            return {
                "provider": "maptiler",
                "style_url": f"{MAPTILER_MAP_STYLE}?key={self.api_key}",
                "tile_url": f"https://api.maptiler.com/maps/streets-v2/{{z}}/{{x}}/{{y}}.png?key={self.api_key}",
                "attribution": "© MapTiler © OpenStreetMap contributors",
                "is_configured": True
            }
        else:
            return {
                "provider": "openstreetmap",
                "style_url": "https://demotiles.maplibre.org/style.json",
                "tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                "attribution": "© OpenStreetMap contributors",
                "is_configured": False,
                "note": "Using standard Leaflet & OpenStreetMap tile layer"
            }

    def geocode(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Geocodes a location query to [latitude, longitude].
        Uses MapTiler if valid, with robust fallback to Nominatim & Geoapify.
        """
        if not query or not query.strip():
            return None

        clean_query = query.strip()

        # 1. Try MapTiler Geocoding if key is valid
        if self.is_configured and self._test_key():
            try:
                url = f"{MAPTILER_GEOCODING_URL}/{clean_query}.json"
                params = {"key": self.api_key, "limit": 1}
                resp = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    features = data.get("features", [])
                    if features:
                        f = features[0]
                        lon, lat = f["geometry"]["coordinates"]
                        place_name = f.get("place_name", clean_query)
                        return {
                            "name": place_name,
                            "lat": lat,
                            "lon": lon,
                            "source": "MapTiler Geocoding"
                        }
            except Exception as e:
                logger.warning(f"MapTiler geocoding call error: {e}")

        # 2. Resilient Nominatim & Geoapify Fallback
        nom_result = nominatim_service.geocode(clean_query)
        if nom_result:
            lat, lon, display_name = nom_result
            return {
                "name": display_name,
                "lat": lat,
                "lon": lon,
                "source": "OpenStreetMap Nominatim"
            }

        return None

    def calculate_route(
        self,
        origin_name: str,
        origin_lat: float,
        origin_lon: float,
        dest_name: str,
        dest_lat: float,
        dest_lon: float
    ) -> Optional[RouteSummary]:
        """Calculates driving route with MapTiler Routing API if configured and authorized."""
        if not self.is_configured or not self._test_key():
            return None

        try:
            url = f"{MAPTILER_ROUTING_URL}/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
            params = {
                "key": self.api_key,
                "geometries": "geojson",
                "overview": "full"
            }
            resp = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                routes = data.get("routes", [])
                if routes:
                    primary = routes[0]
                    dist_km = round(primary.get("distance", 0) / 1000.0, 1)
                    duration_sec = primary.get("duration", 0)
                    duration_min = int(duration_sec / 60)
                    hours = duration_min // 60
                    mins = duration_min % 60
                    duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} mins"

                    geometry = primary.get("geometry", {})

                    return RouteSummary(
                        origin_name=origin_name,
                        origin_coords=[origin_lat, origin_lon],
                        destination_name=dest_name,
                        destination_coords=[dest_lat, dest_lon],
                        distance_km=dist_km,
                        duration_minutes=duration_min,
                        duration_str=duration_str,
                        routing_engine="maptiler",
                        geometry_geojson=geometry
                    )
        except Exception as e:
            logger.warning(f"MapTiler routing failed: {e}")

        return None

    def get_transport_hubs(self, city_name: str, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Generates transit hub markers (Railway Stations, Bus Terminals, Airport) for map display."""
        clean = city_name.split(",")[0].strip()
        return [
            {
                "name": f"{clean} Central Railway Station",
                "type": "railway_station",
                "icon": "🚆",
                "coords": [round(lat + 0.015, 4), round(lon - 0.012, 4)]
            },
            {
                "name": f"{clean} Main Intercity Bus Terminal (ISBT)",
                "type": "bus_terminal",
                "icon": "🚌",
                "coords": [round(lat - 0.012, 4), round(lon + 0.018, 4)]
            },
            {
                "name": f"{clean} Airport Connector",
                "type": "airport",
                "icon": "✈",
                "coords": [round(lat + 0.045, 4), round(lon - 0.040, 4)]
            }
        ]
