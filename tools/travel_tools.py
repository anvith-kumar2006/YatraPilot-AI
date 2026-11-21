"""
YatraPilot AI Travel Tools - Core Functions for Gemini Agent

These 6 tools implement the complete travel planning workflow:
1. get_weather - Current and forecast weather
2. search_attractions - Find tourist attractions
3. estimate_trip_budget - Calculate trip cost
4. generate_itinerary - Create day-by-day plan
5. save_trip - Persist to database (HITL gate)
6. update_itinerary - Modify saved itinerary (HITL gate)

Each tool includes validation, error handling, and logging.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from integrations.travel_apis import create_weather_service, create_places_service
from database.db import get_db
from tools.transport_tool import discover_transportation

logger = logging.getLogger(__name__)

# ============================================================================
# SECURITY: Define allowed columns for UPDATE operations
# ============================================================================

ALLOWED_UPDATE_COLUMNS = {
    'destination',
    'start_date',
    'duration_days',
    'travellers',
    'budget_amount',
    'currency',
    'preferences_json',
    'weather_summary_json',
    'attractions_json',
    'itinerary_json',
    'status'
}

PROTECTED_COLUMNS = {'id', 'channel_name', 'created_at', 'updated_at'}

# Initialize services
_weather_service = None
_places_service = None


def _get_weather_service():
    global _weather_service
    if _weather_service is None:
        _weather_service = create_weather_service()
    return _weather_service


def _get_places_service():
    global _places_service
    if _places_service is None:
        _places_service = create_places_service()
    return _places_service


def _validate_update_columns(changes: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate that changes only contain allowed columns.
    
    Args:
        changes: Dictionary of column updates
        
    Returns:
        (is_valid, error_message)
    """
    if not changes:
        return False, "No changes provided"
    
    if not isinstance(changes, dict):
        return False, "Changes must be a dictionary"
    
    for key in changes.keys():
        if key in PROTECTED_COLUMNS:
            return False, f"Cannot update protected column: {key}"
        
        if key not in ALLOWED_UPDATE_COLUMNS:
            return False, f"Unknown column: {key}. Allowed: {', '.join(sorted(ALLOWED_UPDATE_COLUMNS))}"
    
    return True, ""


# ============================================================================
# TOOL 1: GET_WEATHER
# ============================================================================

def get_weather(
    destination: str,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get weather forecast for a destination.
    
    Args:
        destination: City name (e.g., "Bengaluru", "Coorg")
        date: Specific date (YYYY-MM-DD) or None for current
        
    Returns:
        Dict with weather data:
        {
            "status": "success" | "error",
            "destination": str,
            "temperature": float,
            "humidity": int,
            "wind_speed": float,
            "conditions": str,
            "forecast_days": int
        }
    """
    try:
        # Validate destination
        if not destination or not isinstance(destination, str):
            return {
                "status": "error",
                "message": "destination must be a non-empty string",
                "destination": destination
            }
        
        if len(destination) > 100:
            return {
                "status": "error",
                "message": "destination too long (max 100 characters)",
                "destination": destination
            }
        
        logger.info(f"Tool: get_weather({destination}, {date})")
        
        weather_service = _get_weather_service()
        
        # Get coordinates for destination
        coords = weather_service.get_coordinates(destination)
        if not coords:
            # Try alternate name for common Indian destinations
            alternates = {
                "coorg": "kodagu",
                "kodagu": "coorg",
                "bangalore": "bengaluru",
                "bengaluru": "bangalore",
            }
            alternate_name = alternates.get(destination.lower())
            if alternate_name:
                logger.info(f"Trying alternate name: {alternate_name}")
                coords = weather_service.get_coordinates(alternate_name)
            
            if not coords:
                return {
                    "status": "error",
                    "message": f"Could not find coordinates for {destination}",
                    "destination": destination
                }
        
        # Get forecast (7 days by default)
        forecast = weather_service.get_forecast(coords[0], coords[1], days=7)
        
        # Get first hour weather
        temp = forecast["hourly"]["temperature_2m"][0] if forecast["hourly"]["temperature_2m"] else None
        humidity = forecast["hourly"]["relative_humidity_2m"][0] if forecast["hourly"]["relative_humidity_2m"] else None
        wind = forecast["hourly"]["wind_speed_10m"][0] if forecast["hourly"]["wind_speed_10m"] else None
        
        return {
            "status": "success",
            "destination": destination,
            "latitude": forecast["latitude"],
            "longitude": forecast["longitude"],
            "temperature": round(temp, 1) if temp else None,
            "humidity": int(humidity) if humidity else None,
            "wind_speed": round(wind, 1) if wind else None,
            "timezone": forecast["timezone"],
            "forecast_days": 7,
            "message": f"Weather data retrieved for {destination}"
        }
        
    except Exception as e:
        logger.error(f"get_weather error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "destination": destination
        }


# ============================================================================
# TOOL 2: SEARCH_ATTRACTIONS
# ============================================================================

def search_attractions(
    destination: str,
    preferences: Optional[List[str]] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> Dict[str, Any]:
    """
    Search for tourist attractions near a destination.
    
    Args:
        destination: City name
        preferences: List of attraction types (ignored; Geoapify returns tourism.attraction)
        latitude: Optional latitude (if already geocoded)
        longitude: Optional longitude (if already geocoded)
        
    Returns:
        Dict with attractions
    """
    try:
        # Validate destination
        if not destination or not isinstance(destination, str):
            return {
                "status": "error",
                "message": "destination must be a non-empty string",
                "destination": destination
            }
        
        # Validate coordinates if provided
        if latitude is not None:
            if not isinstance(latitude, (int, float)) or not -90 <= latitude <= 90:
                return {
                    "status": "error",
                    "message": "latitude must be between -90 and 90",
                    "destination": destination
                }
        
        if longitude is not None:
            if not isinstance(longitude, (int, float)) or not -180 <= longitude <= 180:
                return {
                    "status": "error",
                    "message": "longitude must be between -180 and 180",
                    "destination": destination
                }
        
        logger.info(f"Tool: search_attractions({destination}, {preferences})")
        
        # Get coordinates if not provided
        if latitude is None or longitude is None:
            weather_service = _get_weather_service()
            coords = weather_service.get_coordinates(destination)
            if not coords:
                return {
                    "status": "error",
                    "message": f"Could not find coordinates for {destination}",
                    "destination": destination
                }
            latitude, longitude = coords
        
        # Search attractions
        places_service = _get_places_service()
        attractions = places_service.search_attractions(
            latitude=latitude,
            longitude=longitude,
            radius_meters=10000,
            limit=10
        )
        
        return {
            "status": "success",
            "destination": destination,
            "latitude": latitude,
            "longitude": longitude,
            "count": len(attractions),
            "attractions": attractions,
            "message": f"Found {len(attractions)} attractions in {destination}"
        }
        
    except Exception as e:
        logger.error(f"search_attractions error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "destination": destination
        }


# ============================================================================
# TOOL 3: ESTIMATE_TRIP_BUDGET
# ============================================================================

def estimate_trip_budget(
    destination: str,
    duration_days: int,
    travellers: int,
    accommodation_level: str = "mid"
) -> Dict[str, Any]:
    """
    Estimate trip budget based on destination and parameters.
    
    Args:
        destination: City name
        duration_days: Number of days
        travellers: Number of travelers
        accommodation_level: "budget" | "mid" | "luxury" (default: "mid")
        
    Returns:
        Dict with budget breakdown
    """
    try:
        # Validate inputs
        if not destination or not isinstance(destination, str):
            return {
                "status": "error",
                "message": "destination must be a non-empty string"
            }
        
        if not isinstance(duration_days, int) or duration_days < 1:
            return {
                "status": "error",
                "message": "duration_days must be a positive integer"
            }
        
        if duration_days > 365:
            return {
                "status": "error",
                "message": "duration_days cannot exceed 365"
            }
        
        if not isinstance(travellers, int) or travellers < 1:
            return {
                "status": "error",
                "message": "travellers must be a positive integer"
            }
        
        if travellers > 100:
            return {
                "status": "error",
                "message": "travellers cannot exceed 100"
            }
        
        accommodation_level = str(accommodation_level).lower()
        if accommodation_level not in {"budget", "mid", "luxury"}:
            return {
                "status": "error",
                "message": f"accommodation_level must be 'budget', 'mid', or 'luxury'"
            }
        
        logger.info(f"Tool: estimate_trip_budget({destination}, {duration_days} days, {travellers} people)")
        
        # Budget rates (in INR, for India - adjust for other regions)
        rates = {
            "budget": {
                "accommodation": 1000,
                "meals": 500,
                "activities": 1000,
                "transport": 2000
            },
            "mid": {
                "accommodation": 3000,
                "meals": 1500,
                "activities": 2000,
                "transport": 5000
            },
            "luxury": {
                "accommodation": 10000,
                "meals": 5000,
                "activities": 5000,
                "transport": 10000
            }
        }
        
        rate = rates.get(accommodation_level, rates["mid"])
        
        # Calculate breakdown
        accommodation = rate["accommodation"] * duration_days * travellers
        meals = rate["meals"] * duration_days * travellers
        activities = rate["activities"] * duration_days
        transport = rate["transport"]
        
        total = accommodation + meals + activities + transport
        per_person = total / travellers if travellers > 0 else 0
        
        return {
            "status": "success",
            "destination": destination,
            "duration_days": duration_days,
            "travellers": travellers,
            "accommodation_level": accommodation_level,
            "total_budget": round(total, 2),
            "per_person": round(per_person, 2),
            "currency": "INR",
            "breakdown": {
                "accommodation": round(accommodation, 2),
                "meals": round(meals, 2),
                "activities": round(activities, 2),
                "transport": round(transport, 2)
            },
            "message": f"Budget for {destination}: ₹{total:,.0f} total (₹{per_person:,.0f} per person)"
        }
        
    except Exception as e:
        logger.error(f"estimate_trip_budget error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "destination": destination
        }


# ============================================================================
# TOOL 4: GENERATE_ITINERARY
# ============================================================================

def generate_itinerary(
    destination: str,
    start_date: str,
    duration_days: int,
    preferences: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate a day-by-day itinerary.
    
    Args:
        destination: City name
        start_date: Start date (YYYY-MM-DD)
        duration_days: Number of days
        preferences: Optional list of preferences
        
    Returns:
        Dict with itinerary
    """
    try:
        # Validate inputs
        if not destination or not isinstance(destination, str):
            return {
                "status": "error",
                "message": "destination must be a non-empty string"
            }
        
        if not start_date or not isinstance(start_date, str):
            return {
                "status": "error",
                "message": "start_date must be a non-empty string in YYYY-MM-DD format"
            }
        
        if not isinstance(duration_days, int) or duration_days < 1:
            return {
                "status": "error",
                "message": "duration_days must be a positive integer"
            }
        
        logger.info(f"Tool: generate_itinerary({destination}, {start_date}, {duration_days} days)")
        
        # Sample activities per destination
        activity_templates = {
            "default": [
                "Visit local market",
                "Explore main attractions",
                "Try local cuisine",
                "Rest and relax",
                "Evening stroll"
            ]
        }
        
        # Parse start date
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            return {
                "status": "error",
                "message": f"Invalid date format: {start_date}. Use YYYY-MM-DD"
            }
        
        # Generate itinerary
        itinerary = []
        activities_list = activity_templates.get("default", [])
        
        for day in range(1, duration_days + 1):
            current_date = start + timedelta(days=day-1)
            
            itinerary.append({
                "day": day,
                "date": current_date.strftime("%Y-%m-%d"),
                "activities": [
                    f"Activity {day}a: {activities_list[(day-1) % len(activities_list)]}",
                    f"Activity {day}b: Explore {destination}"
                ],
                "meals": [
                    "Breakfast at hotel",
                    f"Lunch at local restaurant",
                    f"Dinner featuring {destination} cuisine"
                ]
            })
        
        return {
            "status": "success",
            "destination": destination,
            "start_date": start_date,
            "duration_days": duration_days,
            "itinerary": itinerary,
            "message": f"Generated {duration_days}-day itinerary for {destination}"
        }
        
    except Exception as e:
        logger.error(f"generate_itinerary error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# TOOL 5: SAVE_TRIP (HITL GATE)
# ============================================================================

def save_trip(
    destination: str,
    start_date: str,
    duration_days: int,
    budget_amount: float,
    itinerary_json: str,
    user_confirmed: bool = False,
    channel_name: str = "unknown"
) -> Dict[str, Any]:
    """
    Save a trip to the database.
    
    HUMAN-IN-THE-LOOP GATE: Only saves if user_confirmed=True.
    If user_confirmed=False, returns APPROVAL_REQUIRED.
    
    Args:
        destination: City name
        start_date: Start date (YYYY-MM-DD)
        duration_days: Number of days
        budget_amount: Total budget
        itinerary_json: Itinerary as JSON string
        user_confirmed: Whether user confirmed the save
        channel_name: Agora channel name (for session tracking)
        
    Returns:
        Dict with trip_id and status
    """
    try:
        # Validate inputs
        if not destination or not isinstance(destination, str):
            return {
                "status": "error",
                "message": "destination must be a non-empty string"
            }
        
        if duration_days < 1 or duration_days > 365:
            return {
                "status": "error",
                "message": "duration_days must be between 1 and 365"
            }
        
        if budget_amount < 0:
            return {
                "status": "error",
                "message": "budget_amount cannot be negative"
            }
        
        logger.info(f"Tool: save_trip({destination}, user_confirmed={user_confirmed})")
        
        if not user_confirmed:
            # HITL: Request confirmation
            logger.warning("save_trip: User confirmation required")
            return {
                "status": "APPROVAL_REQUIRED",
                "message": f"Ready to save {destination} trip. User must confirm.",
                "destination": destination,
                "pending_action": "save_trip",
                "trip_data": {
                    "destination": destination,
                    "start_date": start_date,
                    "duration_days": duration_days,
                    "budget_amount": budget_amount
                }
            }
        
        # User confirmed: Save to database
        db = get_db()
        
        try:
            with db.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO trips (
                        channel_name, destination, start_date, duration_days,
                        budget_amount, itinerary_json, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        channel_name,
                        destination,
                        start_date,
                        duration_days,
                        budget_amount,
                        itinerary_json,
                        "SAVED"
                    )
                )
                trip_id = cursor.fetchone()[0]
            
            logger.info(f"✓ Saved trip {trip_id}: {destination}")
            
            return {
                "status": "success",
                "trip_id": trip_id,
                "message": f"Trip saved successfully (ID: {trip_id})",
                "destination": destination
            }
            
        except Exception as e:
            logger.error(f"Database error saving trip: {e}")
            return {
                "status": "error",
                "message": f"Failed to save trip: {e}"
            }
        
    except Exception as e:
        logger.error(f"save_trip error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# TOOL 6: UPDATE_ITINERARY (HITL GATE) - SECURED
# ============================================================================

def update_itinerary(
    trip_id: int,
    changes: Dict[str, Any],
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    Update an existing trip's itinerary.
    
    HUMAN-IN-THE-LOOP GATE: Only updates if user_confirmed=True.
    
    SECURITY: Column whitelist prevents SQL injection.
    
    Args:
        trip_id: ID of trip to update
        changes: Dict with fields to update (e.g., {"budget_amount": 50000})
        user_confirmed: Whether user confirmed the update
        
    Returns:
        Dict with status
    """
    try:
        # Validate trip_id
        if not isinstance(trip_id, int) or trip_id <= 0:
            return {
                "status": "error",
                "message": "trip_id must be a positive integer"
            }
        
        # Validate changes structure and columns
        is_valid, error_msg = _validate_update_columns(changes)
        if not is_valid:
            logger.warning(f"Invalid update attempt: {error_msg}, changes={changes}")
            return {
                "status": "error",
                "message": error_msg
            }
        
        logger.info(f"Tool: update_itinerary(trip_id={trip_id}, user_confirmed={user_confirmed})")
        
        if not user_confirmed:
            # HITL: Request confirmation
            logger.warning("update_itinerary: User confirmation required")
            return {
                "status": "APPROVAL_REQUIRED",
                "message": f"Ready to update trip {trip_id}. User must confirm.",
                "trip_id": trip_id,
                "pending_action": "update_itinerary",
                "changes": changes
            }
        
        # User confirmed: Update database
        db = get_db()
        
        try:
            with db.get_cursor() as cursor:
                # Build UPDATE statement with validated columns
                set_clauses = []
                params = []
                
                for key, value in changes.items():
                    set_clauses.append(f"{key} = %s")
                    params.append(value)
                
                params.append(trip_id)
                
                query = f"UPDATE trips SET {', '.join(set_clauses)} WHERE id = %s"
                cursor.execute(query, params)
            
            logger.info(f"✓ Updated trip {trip_id}")
            
            return {
                "status": "success",
                "trip_id": trip_id,
                "message": f"Trip {trip_id} updated successfully",
                "changes": changes
            }
            
        except Exception as e:
            logger.error(f"Database error updating trip: {e}")
            return {
                "status": "error",
                "message": f"Failed to update trip: {e}"
            }
        
    except Exception as e:
        logger.error(f"update_itinerary error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

