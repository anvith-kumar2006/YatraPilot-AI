"""
Travel-related external APIs integration for YatraPilot AI.
Includes:
- Open-Meteo: Weather forecasts and geocoding
- Geoapify: Places and attractions search
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Tuple
import openmeteo_requests
import requests_cache
from retry_requests import retry

logger = logging.getLogger(__name__)

# ============================================================================
# OPEN-METEO WEATHER SERVICE
# ============================================================================

class WeatherService:
    """Open-Meteo weather API integration (free, no API key required)."""
    
    def __init__(self):
        """Initialize Open-Meteo client with caching."""
        # Setup caching and retry logic
        self.cache_session = requests_cache.CachedSession(
            ".cache",
            expire_after=3600  # Cache for 1 hour
        )
        self.retry_session = retry(
            self.cache_session,
            retries=3,
            backoff_factor=0.2
        )
        self.client = openmeteo_requests.Client(session=self.retry_session)
    
    def get_coordinates(self, city: str) -> Optional[Tuple[float, float]]:
        """
        Get latitude/longitude for a city name.
        
        Args:
            city: City name (e.g., "Bengaluru", "Mumbai")
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
            
        Raises:
            requests.RequestException: If API call fails
        """
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": city,
                "count": 1,
                "language": "en"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                logger.warning(f"No coordinates found for {city}")
                return None
            
            first_result = results[0]
            lat = first_result.get("latitude")
            lon = first_result.get("longitude")
            
            logger.info(f"✓ Geocoded {city}: {lat}, {lon}")
            return (lat, lon)
            
        except requests.RequestException as e:
            logger.error(f"Geocoding error: {e}")
            raise
    
    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7
    ) -> Dict:
        """
        Get weather forecast for coordinates.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            days: Number of days to forecast (max 16)
            
        Returns:
            Dictionary with hourly weather data
            
        Raises:
            requests.RequestException: If API call fails
        """
        try:
            if days > 16:
                days = 16
                logger.warning("Open-Meteo max forecast is 16 days; limiting to 16")
            
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "precipitation",
                    "wind_speed_10m",
                    "weather_code"
                ],
                "timezone": "auto",
                "forecast_days": days
            }
            
            responses = self.client.weather_api(url, params=params)
            response = responses[0]
            
            # Extract hourly data
            hourly = response.Hourly()
            
            data = {
                "latitude": response.Latitude(),
                "longitude": response.Longitude(),
                "timezone": response.Timezone().decode("utf-8") if isinstance(response.Timezone(), bytes) else response.Timezone(),
                "hourly": {
                    "temperature_2m": hourly.Variables(0).ValuesAsNumpy().tolist(),
                    "relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy().tolist(),
                    "apparent_temperature": hourly.Variables(2).ValuesAsNumpy().tolist(),
                    "precipitation": hourly.Variables(3).ValuesAsNumpy().tolist(),
                    "wind_speed_10m": hourly.Variables(4).ValuesAsNumpy().tolist(),
                    "weather_code": hourly.Variables(5).ValuesAsNumpy().tolist(),
                }
            }
            
            logger.info(f"✓ Fetched {days}-day forecast for ({latitude}, {longitude})")
            return data
            
        except Exception as e:
            logger.error(f"Weather forecast error: {e}")
            raise
    
    def get_weather_summary(self, city: str) -> Optional[Dict]:
        """
        Get current weather summary for a city.
        
        Args:
            city: City name
            
        Returns:
            Dictionary with weather info or None if error
        """
        try:
            coords = self.get_coordinates(city)
            if not coords:
                return None
            
            forecast = self.get_forecast(coords[0], coords[1], days=1)
            
            # Get first hour of forecast
            temp = forecast["hourly"]["temperature_2m"][0] if forecast["hourly"]["temperature_2m"] else None
            humidity = forecast["hourly"]["relative_humidity_2m"][0] if forecast["hourly"]["relative_humidity_2m"] else None
            wind = forecast["hourly"]["wind_speed_10m"][0] if forecast["hourly"]["wind_speed_10m"] else None
            
            return {
                "city": city,
                "latitude": forecast["latitude"],
                "longitude": forecast["longitude"],
                "temperature": temp,
                "humidity": humidity,
                "wind_speed": wind,
                "timezone": forecast["timezone"]
            }
            
        except Exception as e:
            logger.error(f"Weather summary error: {e}")
            return None


# ============================================================================
# GEOAPIFY PLACES SERVICE
# ============================================================================

class PlacesService:
    """Geoapify Places API integration for attractions and POI search."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Geoapify client.
        
        Args:
            api_key: Geoapify API key. If None, uses GEOAPIFY_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GEOAPIFY_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEOAPIFY_API_KEY not found in environment")
        
        self.base_url = "https://api.geoapify.com/v2/places"
    
    def search_attractions(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 10000,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search for tourist attractions near coordinates.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            radius_meters: Search radius in meters
            limit: Max results to return
            
        Returns:
            List of attraction dictionaries
            
        Raises:
            requests.RequestException: If API call fails
        """
        try:
            params = {
                "categories": "tourism.attraction",
                "filter": f"circle:{longitude},{latitude},{radius_meters}",
                "limit": limit,
                "apiKey": self.api_key
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            features = data.get("features", [])
            
            attractions = []
            for feature in features:
                props = feature.get("properties", {})
                attractions.append({
                    "name": props.get("name", "Unnamed"),
                    "address": props.get("formatted", ""),
                    "categories": props.get("categories", []),
                    "latitude": props.get("lat"),
                    "longitude": props.get("lon"),
                    "distance": props.get("distance")
                })
            
            logger.info(f"✓ Found {len(attractions)} attractions near ({latitude}, {longitude})")
            return attractions
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error("Geoapify: Invalid API key")
            elif response.status_code == 429:
                logger.error("Geoapify: Rate limit exceeded")
            else:
                logger.error(f"HTTP error {response.status_code}: {e}")
            raise
        except requests.RequestException as e:
            logger.error(f"Places search error: {e}")
            raise
    
    def search_restaurants(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 5000,
        limit: int = 10
    ) -> List[Dict]:
        """Search for restaurants near coordinates."""
        return self._search_category(
            "amenity.restaurant",
            latitude,
            longitude,
            radius_meters,
            limit
        )
    
    def search_hotels(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 5000,
        limit: int = 10
    ) -> List[Dict]:
        """Search for hotels near coordinates."""
        return self._search_category(
            "accommodation.hotel",
            latitude,
            longitude,
            radius_meters,
            limit
        )
    
    def _search_category(
        self,
        category: str,
        latitude: float,
        longitude: float,
        radius_meters: int,
        limit: int
    ) -> List[Dict]:
        """Generic category search."""
        try:
            params = {
                "categories": category,
                "filter": f"circle:{longitude},{latitude},{radius_meters}",
                "limit": limit,
                "apiKey": self.api_key
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            features = data.get("features", [])
            
            results = []
            for feature in features:
                props = feature.get("properties", {})
                results.append({
                    "name": props.get("name", "Unnamed"),
                    "address": props.get("formatted", ""),
                    "categories": props.get("categories", []),
                    "latitude": props.get("lat"),
                    "longitude": props.get("lon")
                })
            
            logger.info(f"✓ Found {len(results)} {category} near ({latitude}, {longitude})")
            return results
            
        except requests.RequestException as e:
            logger.error(f"Category search error ({category}): {e}")
            raise


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_weather_service() -> WeatherService:
    """Factory function to create weather service."""
    return WeatherService()


def create_places_service() -> PlacesService:
    """Factory function to create places service."""
    return PlacesService(api_key=os.getenv("GEOAPIFY_API_KEY"))
