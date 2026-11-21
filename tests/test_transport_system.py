"""
Comprehensive Transport System & Availability Matrix Verification Test
Tests all endpoints, live data feeds, Neon DB registered fleet, and Gemini integration.
"""

import json
import urllib.request
import urllib.parse
import sys

BASE_URL = "http://127.0.0.1:5000"

def get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "YatraPilot-Test/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode())

def post(path, body):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "YatraPilot-Test/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode())

def run_tests():
    print("=" * 70)
    print("YATRAPILOT AI — TRANSPORTATION SYSTEM VERIFICATION")
    print("=" * 70)

    # 1. Availability Matrix
    print("\n[TEST 1] Testing /api/transport/availability ...")
    status, data = get("/api/transport/availability")
    assert status == 200, f"Expected 200, got {status}"
    summary = data.get("summary", {})
    integrations = data.get("integrations", [])
    print(f"  Status: {status} OK")
    print(f"  Total Evaluated: {data.get('total_services')}")
    print(f"  Summary: {summary}")
    for item in integrations:
        print(f"    - {item['service']:<20}: {item['status']:<20} ({item['category']})")

    # 2. Map Config
    print("\n[TEST 2] Testing /api/transport/map-config ...")
    status, data = get("/api/transport/map-config")
    assert status == 200
    print(f"  Status: {status} OK")
    print(f"  Map Provider: {data.get('provider')}")
    print(f"  Tile URL: {data.get('tile_url')}")

    # 3. Route Calculation (OSRM / Nominatim fallback)
    print("\n[TEST 3] Testing /api/transport/route (Delhi -> Jaipur) ...")
    status, data = get("/api/transport/route?origin=Delhi&destination=Jaipur")
    assert status == 200
    route = data.get("route") or {}
    print(f"  Status: {status} OK")
    print(f"  Distance: {route.get('distance_km')} km")
    print(f"  Duration: {route.get('duration_str')}")
    print(f"  Routing Engine: {route.get('routing_engine')}")
    print(f"  Geometry: {bool(route.get('geometry_geojson'))}")

    # 4. Registered Providers from Neon DB
    print("\n[TEST 4] Testing /api/transport/registered-providers ...")
    status, data = get("/api/transport/registered-providers")
    assert status == 200
    providers = data.get("providers", [])
    print(f"  Status: {status} OK")
    print(f"  Registered Count: {len(providers)}")
    for p in providers:
        print(f"    - {p.get('provider_name')} ({p.get('category')}) | Phone: {p.get('contact_phone')} | Rating: {p.get('rating')}")

    # 5. Marketplace Search across all categories
    print("\n[TEST 5] Testing /api/transport/search (Delhi -> Jaipur, 12 passengers) ...")
    status, data = post("/api/transport/search", {
        "origin": "Delhi",
        "destination": "Jaipur",
        "passengers": 12,
        "category": "all"
    })
    assert status == 200
    options = data.get("options", [])
    print(f"  Status: {status} OK")
    print(f"  Total Options Returned: {len(options)}")
    
    cat_counts = {}
    neon_count = 0
    for opt in options:
        cat = opt.get("category")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        if opt.get("details", {}).get("is_neon_registered") or "Neon DB" in opt.get("source", ""):
            neon_count += 1
    print(f"  Categories breakdown: {cat_counts}")
    print(f"  Neon DB Verified Options: {neon_count}")

    # 6. Filter by Registered Fleet
    print("\n[TEST 6] Testing /api/transport/search with category='registered_fleet' ...")
    status, data = post("/api/transport/search", {
        "origin": "Delhi",
        "destination": "Jaipur",
        "passengers": 12,
        "category": "registered_fleet"
    })
    assert status == 200
    reg_options = data.get("options", [])
    print(f"  Status: {status} OK")
    print(f"  Registered Fleet Options Count: {len(reg_options)}")
    for r in reg_options[:3]:
        print(f"    - {r.get('title')} | Operator: {r.get('operator')} | Fare: {r.get('price_range')}")

    # 7. Transit Feeds
    print("\n[TEST 7] Testing /api/transport/feeds ...")
    status, data = get("/api/transport/feeds")
    assert status == 200
    print(f"  Status: {status} OK")
    print(f"  India GTFS Feeds: {len(data.get('india_gtfs_feeds', []))}")
    print(f"  Mobility DB Catalog: {len(data.get('mobility_database_feeds', []))}")

    # 8. Test Gemini Integration with discover_transportation tool
    print("\n[TEST 8] Testing /api/chat with transport inquiry ...")
    status, data = post("/api/chat", {
        "message": "Find tempo traveller options for 12 people traveling from Delhi to Jaipur tomorrow",
        "session_id": "test_transport_session"
    })
    assert status == 200
    reply = data.get("reply", "")
    print(f"  Status: {status} OK")
    print(f"  Gemini Reply (first 250 chars):\n    {reply[:250]}...")

    print("\n" + "=" * 70)
    print("ALL 8 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
