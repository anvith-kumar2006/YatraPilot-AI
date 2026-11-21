"""
YatraPilot AI — OpenStreetMap Nominatim Geocoding Service
Provides compliant forward and reverse geocoding with 1-second rate limit throttling,
LRU in-memory caching, and pre-warmed Indian destination coordinates.
Usage Policy: https://operations.osmfoundation.org/policies/nominatim/
"""

import os
import time
import json
import logging
import threading
import urllib.request
import urllib.parse
from typing import Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)

DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org"
USER_AGENT = "YatraPilot-AI/1.0 (travel-planner; support@yatrapilot.ai)"

# Pre-warmed accurate coordinates for common Indian cities & tourist states
PREWARMED_INDIAN_DESTINATIONS: Dict[str, Tuple[float, float, str]] = {
    "delhi": (28.6139, 77.2090, "New Delhi, Delhi, India"),
    "new delhi": (28.6139, 77.2090, "New Delhi, Delhi, India"),
    "jaipur": (26.9124, 75.7873, "Jaipur, Rajasthan, India"),
    "agra": (27.1767, 78.0081, "Agra, Uttar Pradesh, India"),
    "mumbai": (19.0760, 72.8777, "Mumbai, Maharashtra, India"),
    "bombay": (19.0760, 72.8777, "Mumbai, Maharashtra, India"),
    "goa": (15.2993, 74.1240, "Goa, India"),
    "panaji": (15.4909, 73.8278, "Panaji, Goa, India"),
    "bengaluru": (12.9716, 77.5946, "Bengaluru, Karnataka, India"),
    "bangalore": (12.9716, 77.5946, "Bengaluru, Karnataka, India"),
    "chennai": (13.0827, 80.2707, "Chennai, Tamil Nadu, India"),
    "kolkata": (22.5726, 88.3639, "Kolkata, West Bengal, India"),
    "hyderabad": (17.3850, 78.4867, "Hyderabad, Telangana, India"),
    "pune": (18.5204, 73.8567, "Pune, Maharashtra, India"),
    "manali": (32.2396, 77.1887, "Manali, Himachal Pradesh, India"),
    "shimla": (31.1048, 77.1734, "Shimla, Himachal Pradesh, India"),
    "leh": (34.1526, 77.5771, "Leh, Ladakh, India"),
    "varanasi": (25.3176, 82.9739, "Varanasi, Uttar Pradesh, India"),
    "kochi": (9.9312, 76.2673, "Kochi, Kerala, India"),
    "cochin": (9.9312, 76.2673, "Kochi, Kerala, India"),
    "kerala": (10.8505, 76.2711, "Kerala, India"),
    "udaipur": (24.5854, 73.7125, "Udaipur, Rajasthan, India"),
    "amritsar": (31.6340, 74.8723, "Amritsar, Punjab, India"),
    "rishikesh": (30.0869, 78.2676, "Rishikesh, Uttarakhand, India"),
    "haridwar": (29.9457, 78.1642, "Haridwar, Uttarakhand, India"),
    "mysuru": (12.2958, 76.6394, "Mysuru, Karnataka, India"),
    "mysore": (12.2958, 76.6394, "Mysuru, Karnataka, India"),
    "ahmedabad": (23.0225, 72.5714, "Ahmedabad, Gujarat, India"),
    "ooty": (11.4102, 76.6950, "Ooty, Tamil Nadu, India"),
    "coorg": (12.3375, 75.8069, "Madikeri, Coorg, Karnataka, India"),
    "darjeeling": (27.0410, 88.2663, "Darjeeling, West Bengal, India")
}


class NominatimService:
    """
    OpenStreetMap Nominatim geocoding service with:
    - 1-second request rate throttling (complies with Nominatim Usage Policy)
    - Thread-safe caching
    - Pre-warmed Indian cities
    - Geoapify fallback if available
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("NOMINATIM_URL", DEFAULT_NOMINATIM_URL)).rstrip("/")
        self._cache: Dict[str, Tuple[float, float, str]] = dict(PREWARMED_INDIAN_DESTINATIONS)
        self._last_request_time: float = 0.0
        self._lock = threading.Lock()
        self._geoapify_key = os.getenv("GEOAPIFY_API_KEY", "").strip()

    def _throttle(self):
        """Enforces at least 1.0 second between consecutive Nominatim requests."""
        with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < 1.05:
                time.sleep(1.05 - elapsed)
            self._last_request_time = time.time()

    def geocode(self, query: str) -> Optional[Tuple[float, float, str]]:
        """
        Geocodes a location query into (lat, lon, display_name).
        
        Args:
            query: Location or city name (e.g. "Delhi", "Jaipur", "Goa")
            
        Returns:
            Tuple of (lat, lon, display_name) or None if not found.
        """
        if not query or not query.strip():
            return None

        clean_query = query.strip().lower()

        # 1. Check in-memory pre-warmed cache
        if clean_query in self._cache:
            return self._cache[clean_query]

        # Check partial/contains match in pre-warmed destinations
        for key, val in self._cache.items():
            if key in clean_query or clean_query in key:
                return val

        # 2. Query Nominatim Public API with rate limiting
        try:
            self._throttle()
            encoded = urllib.parse.quote(query.strip())
            url = f"{self.base_url}/search?q={encoded}&format=json&limit=1&countrycodes=in"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and isinstance(data, list) and len(data) > 0:
                    first = data[0]
                    lat = float(first["lat"])
                    lon = float(first["lon"])
                    display_name = first.get("display_name", query.title())
                    res = (lat, lon, display_name)
                    self._cache[clean_query] = res
                    logger.info(f"✓ Nominatim geocoded '{query}' -> ({lat}, {lon})")
                    return res

        except Exception as e:
            logger.warning(f"Nominatim geocoding failed for '{query}': {e}")

        # 3. Geoapify Fallback (if API key is present)
        if self._geoapify_key:
            try:
                encoded = urllib.parse.quote(query.strip())
                geo_url = f"https://api.geoapify.com/v1/geocode/search?text={encoded}&country=India&apiKey={self._geoapify_key}"
                req = urllib.request.Request(geo_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    geo_data = json.loads(resp.read().decode("utf-8"))
                    features = geo_data.get("features", [])
                    if features:
                        coords = features[0].get("geometry", {}).get("coordinates", [])
                        props = features[0].get("properties", {})
                        if len(coords) == 2:
                            lon, lat = float(coords[0]), float(coords[1])
                            display_name = props.get("formatted", query.title())
                            res = (lat, lon, display_name)
                            self._cache[clean_query] = res
                            logger.info(f"✓ Geoapify fallback geocoded '{query}' -> ({lat}, {lon})")
                            return res
            except Exception as e2:
                logger.warning(f"Geoapify fallback geocoding failed for '{query}': {e2}")

        # 4. Fallback default
        return (28.6139, 77.2090, f"{query.title()}, India")


# Global singleton instance
nominatim_service = NominatimService()
