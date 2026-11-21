"""
YatraPilot AI — OSRM (Open Source Routing Machine) Service
Calculates road-routes, driving distances, travel durations, and GeoJSON route paths.
Features:
- Live OSRM driving engine
- In-memory route caching
- Secondary fallback to live Geoapify Routing API
- Resilient Haversine road network estimation
Website: https://project-osrm.org/
"""

import os
import math
import logging
import requests
from typing import Dict, List, Optional, Tuple, Any
from .base import RouteSummary

logger = logging.getLogger(__name__)

DEFAULT_OSRM_URL = "https://router.project-osrm.org"
USER_AGENT = "YatraPilot-AI/1.0 (travel-planner; support@yatrapilot.ai)"


class OSRMService:
    """Road routing service with OSRM, caching, and Geoapify fallback."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OSRM_ROUTING_URL", DEFAULT_OSRM_URL)).rstrip("/")
        self._geoapify_key = os.getenv("GEOAPIFY_API_KEY", "").strip()
        self._cache: Dict[str, RouteSummary] = {}

    def calculate_driving_route(
        self,
        origin_name: str,
        origin_lat: float,
        origin_lon: float,
        dest_name: str,
        dest_lat: float,
        dest_lon: float
    ) -> RouteSummary:
        """
        Calculates road route between origin and destination coordinates.
        Uses in-memory cache, OSRM public API, Geoapify fallback, and Haversine estimation.
        """
        cache_key = f"{round(origin_lat, 3)},{round(origin_lon, 3)}->{round(dest_lat, 3)},{round(dest_lon, 3)}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            # Return fresh summary object with current city names
            return RouteSummary(
                origin_name=origin_name,
                origin_coords=[origin_lat, origin_lon],
                destination_name=dest_name,
                destination_coords=[dest_lat, dest_lon],
                distance_km=cached.distance_km,
                duration_minutes=cached.duration_minutes,
                duration_str=cached.duration_str,
                routing_engine=cached.routing_engine,
                geometry_geojson=cached.geometry_geojson,
                waypoints=cached.waypoints
            )

        # 1. Primary: OSRM Route API
        try:
            # OSRM coordinate order is {lon},{lat}
            url = f"{self.base_url}/route/v1/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
            params = {
                "overview": "full",
                "geometries": "geojson",
                "alternatives": "false",
                "steps": "false"
            }
            headers = {"User-Agent": USER_AGENT}
            resp = requests.get(url, params=params, headers=headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    primary_route = data["routes"][0]
                    distance_km = round(primary_route.get("distance", 0) / 1000.0, 1)
                    duration_sec = primary_route.get("duration", 0)
                    duration_min = int(duration_sec / 60)
                    hours = duration_min // 60
                    mins = duration_min % 60
                    duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} mins"

                    geometry = primary_route.get("geometry", {})

                    logger.info(f"✓ OSRM Route: {origin_name} -> {dest_name}: {distance_km}km, {duration_str}")

                    summary = RouteSummary(
                        origin_name=origin_name,
                        origin_coords=[origin_lat, origin_lon],
                        destination_name=dest_name,
                        destination_coords=[dest_lat, dest_lon],
                        distance_km=distance_km,
                        duration_minutes=duration_min,
                        duration_str=duration_str,
                        routing_engine="osrm",
                        geometry_geojson=geometry
                    )
                    self._cache[cache_key] = summary
                    return summary
        except Exception as e:
            logger.warning(f"OSRM routing failed ({e}), checking Geoapify fallback...")

        # 2. Secondary: Geoapify Routing API (if key available)
        if self._geoapify_key:
            try:
                geo_url = f"https://api.geoapify.com/v1/routing?waypoints={origin_lat},{origin_lon}|{dest_lat},{dest_lon}&mode=drive&apiKey={self._geoapify_key}"
                resp = requests.get(geo_url, headers={"User-Agent": USER_AGENT}, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    features = data.get("features", [])
                    if features:
                        feature = features[0]
                        props = feature.get("properties", {})
                        distance_meters = props.get("distance", 0)
                        distance_km = round(distance_meters / 1000.0, 1)
                        duration_sec = props.get("time", 0)
                        duration_min = int(duration_sec / 60)
                        hours = duration_min // 60
                        mins = duration_min % 60
                        duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} mins"
                        geometry = feature.get("geometry", {})

                        logger.info(f"✓ Geoapify Route: {origin_name} -> {dest_name}: {distance_km}km, {duration_str}")

                        summary = RouteSummary(
                            origin_name=origin_name,
                            origin_coords=[origin_lat, origin_lon],
                            destination_name=dest_name,
                            destination_coords=[dest_lat, dest_lon],
                            distance_km=distance_km,
                            duration_minutes=duration_min,
                            duration_str=duration_str,
                            routing_engine="geoapify",
                            geometry_geojson=geometry
                        )
                        self._cache[cache_key] = summary
                        return summary
            except Exception as e2:
                logger.warning(f"Geoapify routing failed ({e2}), falling back to highway estimation.")

        # 3. Tertiary: Resilient Highway Estimation (Haversine + Curvature)
        summary = self._fallback_route_estimation(
            origin_name, origin_lat, origin_lon, dest_name, dest_lat, dest_lon
        )
        self._cache[cache_key] = summary
        return summary

    def _fallback_route_estimation(
        self,
        origin_name: str,
        origin_lat: float,
        origin_lon: float,
        dest_name: str,
        dest_lat: float,
        dest_lon: float
    ) -> RouteSummary:
        """
        Computes accurate driving distance estimate based on Great Circle Haversine
        with standard road curvature factor (~1.22x) and average speed ~60 km/h.
        """
        # Haversine formula
        r = 6371.0  # Earth radius in km
        d_lat = math.radians(dest_lat - origin_lat)
        d_lon = math.radians(dest_lon - origin_lon)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(origin_lat))
            * math.cos(math.radians(dest_lat))
            * math.sin(d_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        aerial_km = r * c

        # Apply Indian highway curvature index
        road_distance_km = round(aerial_km * 1.22, 1)

        # Average driving speed in India ~ 60 km/h
        avg_speed_kmh = 60.0
        duration_hours = max(0.5, road_distance_km / avg_speed_kmh)
        duration_min = int(duration_hours * 60)
        hours = duration_min // 60
        mins = duration_min % 60
        duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} mins"

        # Interpolated LineString geometry
        mid_lon = round((origin_lon + dest_lon) / 2 + 0.05, 4)
        mid_lat = round((origin_lat + dest_lat) / 2 + 0.05, 4)
        geometry = {
            "type": "LineString",
            "coordinates": [
                [origin_lon, origin_lat],
                [mid_lon, mid_lat],
                [dest_lon, dest_lat]
            ]
        }

        return RouteSummary(
            origin_name=origin_name,
            origin_coords=[origin_lat, origin_lon],
            destination_name=dest_name,
            destination_coords=[dest_lat, dest_lon],
            distance_km=road_distance_km,
            duration_minutes=duration_min,
            duration_str=duration_str,
            routing_engine="direct_estimate",
            geometry_geojson=geometry
        )
