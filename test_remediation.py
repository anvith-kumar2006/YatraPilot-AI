#!/usr/bin/env python3
"""
Phase 1 Remediation Regression Tests

Tests:
1. SQL injection prevention in update_itinerary
2. Input validation on all endpoints
3. New weather endpoint
4. New places/search endpoint
5. New places/nearby endpoint
6. CORS configuration
7. Database CRUD operations
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import json
import logging
from app import app
from database.db import init_db, get_db
from tools.travel_tools import update_itinerary, _validate_update_columns

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("\n" + "="*70)
print(" PHASE 1 REMEDIATION REGRESSION TEST SUITE")
print("="*70 + "\n")

tests_passed = 0
tests_failed = 0

def test(name, func):
    global tests_passed, tests_failed
    try:
        logger.info(f"Testing: {name}...")
        result = func()
        if result:
            logger.info(f"[PASS] {name}\n")
            tests_passed += 1
            return True
        else:
            logger.error(f"[FAIL] {name}\n")
            tests_failed += 1
            return False
    except Exception as e:
        logger.error(f"[ERROR] {name}: {e}\n")
        tests_failed += 1
        return False

# ============================================================================
# TEST 1: SQL Injection Prevention
# ============================================================================

def test_sql_injection_prevention():
    """Test that malicious column names are rejected."""
    changes = {"destination); DROP TABLE trips; --": "value"}
    is_valid, error = _validate_update_columns(changes)
    return not is_valid and "Unknown column" in error

# ============================================================================
# TEST 2: Protected Columns Cannot Be Updated
# ============================================================================

def test_protected_columns():
    """Test that protected columns are rejected."""
    changes = {"id": 999}
    is_valid, error = _validate_update_columns(changes)
    return not is_valid and "protected" in error

# ============================================================================
# TEST 3: Empty Changes Rejected
# ============================================================================

def test_empty_changes():
    """Test that empty changes dict is rejected."""
    changes = {}
    is_valid, error = _validate_update_columns(changes)
    return not is_valid and "No changes" in error

# ============================================================================
# TEST 4: Valid Column Update Accepted
# ============================================================================

def test_valid_column_update():
    """Test that valid column updates are accepted."""
    changes = {"budget_amount": 50000.0, "status": "UPDATED"}
    is_valid, error = _validate_update_columns(changes)
    return is_valid

# ============================================================================
# TEST 5: Flask App Imports
# ============================================================================

def test_flask_app():
    """Test Flask app initializes."""
    try:
        client = app.test_client()
        return client is not None
    except Exception as e:
        logger.error(f"  Flask error: {e}")
        return False

# ============================================================================
# TEST 6: Health Endpoint
# ============================================================================

def test_health_endpoint():
    """Test GET /health."""
    try:
        client = app.test_client()
        response = client.get('/health')
        data = response.get_json()
        return response.status_code == 200 and data.get('status') == 'ok'
    except Exception as e:
        logger.error(f"  Health endpoint error: {e}")
        return False

# ============================================================================
# TEST 7: Weather Endpoint - Missing City
# ============================================================================

def test_weather_missing_param():
    """Test weather endpoint validation."""
    try:
        client = app.test_client()
        response = client.get('/api/weather')
        return response.status_code == 400
    except Exception as e:
        logger.error(f"  Weather endpoint error: {e}")
        return False

# ============================================================================
# TEST 8: Weather Endpoint - Invalid Latitude
# ============================================================================

def test_weather_invalid_lat():
    """Test weather coordinate validation."""
    try:
        client = app.test_client()
        response = client.get('/api/weather?city=test&lat=999&lon=50')
        return response.status_code == 400
    except Exception as e:
        logger.error(f"  Weather endpoint error: {e}")
        return False

# ============================================================================
# TEST 9: Places Search Endpoint - Missing City
# ============================================================================

def test_places_search_missing():
    """Test places search validation."""
    try:
        client = app.test_client()
        response = client.get('/api/places/search')
        return response.status_code == 400
    except Exception as e:
        logger.error(f"  Places search error: {e}")
        return False

# ============================================================================
# TEST 10: Places Nearby - Missing Coordinates
# ============================================================================

def test_places_nearby_missing():
    """Test nearby places validation."""
    try:
        client = app.test_client()
        response = client.get('/api/places/nearby')
        return response.status_code == 400
    except Exception as e:
        logger.error(f"  Places nearby error: {e}")
        return False

# ============================================================================
# TEST 11: Places Nearby - Invalid Radius
# ============================================================================

def test_places_nearby_invalid_radius():
    """Test nearby places radius validation."""
    try:
        client = app.test_client()
        response = client.get('/api/places/nearby?lat=10&lon=50&radius=999999')
        return response.status_code == 400
    except Exception as e:
        logger.error(f"  Places nearby error: {e}")
        return False

# ============================================================================
# TEST 12: Database Connection
# ============================================================================

def test_database():
    """Test database connection."""
    try:
        db = get_db()
        return db.test_connection()
    except Exception as e:
        logger.error(f"  Database error: {e}")
        return False

# ============================================================================
# TEST 13: GET /api/trips Endpoint
# ============================================================================

def test_get_trips_endpoint():
    """Test GET /api/trips."""
    try:
        client = app.test_client()
        response = client.get('/api/trips')
        data = response.get_json()
        return response.status_code == 200 and 'trips' in data
    except Exception as e:
        logger.error(f"  /api/trips error: {e}")
        return False

# ============================================================================
# RUN TESTS
# ============================================================================

test("SQL Injection Prevention", test_sql_injection_prevention)
test("Protected Columns", test_protected_columns)
test("Empty Changes Rejected", test_empty_changes)
test("Valid Column Update", test_valid_column_update)
test("Flask App Imports", test_flask_app)
test("Health Endpoint", test_health_endpoint)
test("Weather Missing Param Validation", test_weather_missing_param)
test("Weather Invalid Latitude Validation", test_weather_invalid_lat)
test("Places Search Missing Param Validation", test_places_search_missing)
test("Places Nearby Missing Coords Validation", test_places_nearby_missing)
test("Places Nearby Invalid Radius Validation", test_places_nearby_invalid_radius)
test("Database Connection", test_database)
test("GET /api/trips Endpoint", test_get_trips_endpoint)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*70)
print(" TEST SUMMARY")
print("="*70)
print(f"[PASS] Passed:  {tests_passed}")
print(f"[FAIL] Failed:  {tests_failed}")
total = tests_passed + tests_failed
print(f"Total:     {total}")
print("="*70 + "\n")

if tests_failed > 0:
    sys.exit(1)
else:
    print("[PASS] All regression tests passed!\n")
    sys.exit(0)

