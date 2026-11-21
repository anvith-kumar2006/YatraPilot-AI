#!/usr/bin/env python3
"""
YatraPilot AI - Phase 1 Integration Tests

Tests all core components:
1. Database connectivity
2. Flask application startup
3. Individual API integrations
4. Tool functionality
5. API endpoints
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Fix Windows encoding issue
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("\n" + "="*70)
print(" YATRAPILOT AI - PHASE 1 INTEGRATION TEST")
print("="*70 + "\n")

tests_passed = 0
tests_failed = 0
tests_skipped = 0


def test(name: str, func):
    """Run a test and track results."""
    global tests_passed, tests_failed, tests_skipped
    try:
        logger.info(f"Testing: {name}...")
        result = func()
        if result is None or result == True:
            logger.info(f"[PASS] {name}\n")
            tests_passed += 1
        else:
            logger.error(f"[FAIL] {name}\n")
            tests_failed += 1
    except Exception as e:
        logger.error(f"[ERROR] {name}: {e}\n")
        tests_failed += 1


# ============================================================================
# TEST 1: Database Connectivity
# ============================================================================

def test_database_connection():
    """Test PostgreSQL connection to Neon."""
    try:
        from database.db import get_db
        db = get_db()
        return db.test_connection()
    except Exception as e:
        logger.error(f"Database error: {e}")
        return False


# ============================================================================
# TEST 2: Flask App Initialization
# ============================================================================

def test_flask_startup():
    """Test Flask app initialization."""
    try:
        from app import app
        logger.info(f"  Flask app created: {app.name}")
        logger.info(f"  Config: {type(app.config).__name__}")
        logger.info(f"  Debug: {app.debug}")
        return True
    except Exception as e:
        logger.error(f"Flask error: {e}")
        return False


# ============================================================================
# TEST 3: Health Endpoint
# ============================================================================

def test_health_endpoint():
    """Test /health endpoint."""
    try:
        from app import app
        client = app.test_client()
        response = client.get('/health')
        data = response.get_json()
        
        if response.status_code == 200 and data.get('status') == 'ok':
            logger.info(f"  Status: {data['status']}")
            logger.info(f"  Environment: {data.get('environment')}")
            return True
        else:
            logger.error(f"  Unexpected response: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Health endpoint error: {e}")
        return False


# ============================================================================
# TEST 4: Weather Service
# ============================================================================

def test_weather_service():
    """Test Open-Meteo weather integration."""
    try:
        from integrations.travel_apis import create_weather_service
        weather = create_weather_service()
        
        # Test geocoding
        coords = weather.get_coordinates("Bengaluru")
        if not coords:
            logger.error("Could not geocode Bengaluru")
            return False
        
        logger.info(f"  Geocoded Bengaluru: {coords}")
        
        # Test forecast
        forecast = weather.get_forecast(coords[0], coords[1], days=1)
        if not forecast:
            logger.error("Could not fetch forecast")
            return False
        
        temp = forecast["hourly"]["temperature_2m"][0] if forecast["hourly"]["temperature_2m"] else None
        logger.info(f"  Current temp: {temp}°C")
        
        return True
    except Exception as e:
        logger.error(f"Weather service error: {e}")
        return False


# ============================================================================
# TEST 5: Places Service
# ============================================================================

def test_places_service():
    """Test Geoapify places integration."""
    try:
        from integrations.travel_apis import create_places_service
        places = create_places_service()
        
        # Use Bengaluru coordinates
        attractions = places.search_attractions(
            latitude=12.9716,
            longitude=77.5946,
            radius_meters=10000,
            limit=5
        )
        
        logger.info(f"  Found {len(attractions)} attractions")
        if attractions:
            logger.info(f"  Example: {attractions[0]['name']}")
        
        return len(attractions) > 0
    except Exception as e:
        logger.error(f"Places service error: {e}")
        return False


# ============================================================================
# TEST 6: Weather Tool
# ============================================================================

def test_weather_tool():
    """Test get_weather tool."""
    try:
        from tools.travel_tools import get_weather
        result = get_weather("Coorg")
        
        if result.get("status") == "success":
            logger.info(f"  Destination: {result['destination']}")
            logger.info(f"  Temperature: {result.get('temperature')}°C")
            logger.info(f"  Humidity: {result.get('humidity')}%")
            return True
        else:
            logger.error(f"  Tool error: {result.get('message')}")
            return False
    except Exception as e:
        logger.error(f"Weather tool error: {e}")
        return False


# ============================================================================
# TEST 7: Attractions Tool
# ============================================================================

def test_attractions_tool():
    """Test search_attractions tool."""
    try:
        from tools.travel_tools import search_attractions
        result = search_attractions("Goa")
        
        if result.get("status") == "success":
            logger.info(f"  Destination: {result['destination']}")
            logger.info(f"  Attractions found: {result.get('count')}")
            return True
        else:
            logger.error(f"  Tool error: {result.get('message')}")
            return False
    except Exception as e:
        logger.error(f"Attractions tool error: {e}")
        return False


# ============================================================================
# TEST 8: Budget Tool
# ============================================================================

def test_budget_tool():
    """Test estimate_trip_budget tool."""
    try:
        from tools.travel_tools import estimate_trip_budget
        result = estimate_trip_budget(
            destination="Jaipur",
            duration_days=3,
            travellers=2,
            accommodation_level="mid"
        )
        
        if result.get("status") == "success":
            logger.info(f"  Destination: {result['destination']}")
            logger.info(f"  Duration: {result['duration_days']} days")
            logger.info(f"  Budget: ₹{result['total_budget']:,.0f} total")
            logger.info(f"  Per person: ₹{result['per_person']:,.0f}")
            return True
        else:
            logger.error(f"  Tool error: {result.get('message')}")
            return False
    except Exception as e:
        logger.error(f"Budget tool error: {e}")
        return False


# ============================================================================
# TEST 9: Itinerary Tool
# ============================================================================

def test_itinerary_tool():
    """Test generate_itinerary tool."""
    try:
        from tools.travel_tools import generate_itinerary
        result = generate_itinerary(
            destination="Delhi",
            start_date="2024-12-15",
            duration_days=2
        )
        
        if result.get("status") == "success":
            logger.info(f"  Destination: {result['destination']}")
            logger.info(f"  Duration: {result['duration_days']} days")
            logger.info(f"  Days generated: {len(result.get('itinerary', []))}")
            return True
        else:
            logger.error(f"  Tool error: {result.get('message')}")
            return False
    except Exception as e:
        logger.error(f"Itinerary tool error: {e}")
        return False


# ============================================================================
# TEST 10: Gemini Agent
# ============================================================================

def test_gemini_agent():
    """Test Gemini agent initialization."""
    try:
        from integrations.gemini import create_gemini_agent
        agent = create_gemini_agent()
        
        # Register a tool
        from tools.travel_tools import get_weather
        agent.register_tool(
            "get_weather",
            get_weather,
            "Get weather",
            {"properties": {"destination": {"type": "string"}}, "required": ["destination"]}
        )
        
        logger.info(f"  Agent created: {type(agent).__name__}")
        logger.info(f"  Tools registered: 1")
        
        return True
    except Exception as e:
        logger.error(f"Gemini agent error: {e}")
        return False


# ============================================================================
# TEST 11: Agora Client
# ============================================================================

def test_agora_client():
    """Test Agora client initialization."""
    try:
        from integrations.agora import create_agora_client
        agora = create_agora_client()
        
        logger.info(f"  Agora client created: {type(agora).__name__}")
        logger.info(f"  App ID: {agora.app_id[:8]}...")
        
        return True
    except Exception as e:
        logger.error(f"Agora client error: {e}")
        return False


# ============================================================================
# TEST 12: API Endpoints
# ============================================================================

def test_api_endpoints():
    """Test Flask API endpoints."""
    try:
        from app import app
        client = app.test_client()
        
        # Test GET /api/trips
        response = client.get('/api/trips')
        logger.info(f"  GET /api/trips: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"  Expected 200, got {response.status_code}")
            return False
        
        data = response.get_json()
        if not data.get('trips') is not None:
            logger.error("  No 'trips' key in response")
            return False
        
        logger.info(f"  Trips in database: {len(data.get('trips', []))}")
        
        return True
    except Exception as e:
        logger.error(f"API endpoint error: {e}")
        return False


# ============================================================================
# RUN ALL TESTS
# ============================================================================

# Run tests
test("Database Connection", test_database_connection)
test("Flask Startup", test_flask_startup)
test("Health Endpoint", test_health_endpoint)
test("Weather Service", test_weather_service)
test("Places Service", test_places_service)
test("Weather Tool", test_weather_tool)
test("Attractions Tool", test_attractions_tool)
test("Budget Tool", test_budget_tool)
test("Itinerary Tool", test_itinerary_tool)
test("Gemini Agent", test_gemini_agent)
test("Agora Client", test_agora_client)
test("API Endpoints", test_api_endpoints)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*70)
print(" TEST SUMMARY")
print("="*70)
print(f"[PASS] Passed:  {tests_passed}")
print(f"[FAIL] Failed:  {tests_failed}")
print(f"[SKIP] Skipped: {tests_skipped}")
print(f"Total:     {tests_passed + tests_failed + tests_skipped}")
print("="*70 + "\n")

if tests_failed > 0:
    sys.exit(1)
else:
    print("[PASS] All tests passed!\n")
    sys.exit(0)
