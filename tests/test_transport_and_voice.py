"""
End-to-end verification script for:
1. Transportation Discovery & Provider Marketplace
2. 5-Second Silence Auto-Submission
"""
import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_homepage():
    req = urllib.request.Request(f"{BASE_URL}/")
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        assert "transportPage" in html, "transportPage element missing from index.html"
        assert "voiceSilenceCountdown" in html, "voiceSilenceCountdown missing from index.html"
        assert "leaflet.js" in html, "Leaflet JS missing from index.html"
        assert "showTransportMarketplace()" in html, "showTransportMarketplace link missing"
        print("OK Homepage rendered with transportPage, silenceCountdown, and Leaflet!")

def test_transport_categories():
    req = urllib.request.Request(f"{BASE_URL}/api/transport/categories")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        categories = [c["id"] for c in data.get("categories", [])]
        expected = ["bus", "train", "flight", "taxi", "car_rental", "tempo_traveller", "private_coach"]
        for cat in expected:
            assert cat in categories, f"Category {cat} missing"
        print(f"OK All 7 Transport categories verified: {categories}")

def test_transport_search():
    payload = json.dumps({
        "origin": "Delhi",
        "destination": "Jaipur",
        "passengers": 12,
        "category": "all"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/transport/search",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert "options" in data, "options key missing from search response"
        options = data["options"]
        total = data.get("total_options", len(options))
        assert len(options) > 0, "No options returned"
        categories = {opt["category"] for opt in options}
        assert "tempo_traveller" in categories, "Tempo travellers missing from options"
        assert "bus" in categories, "Buses missing from options"
        assert "train" in categories, "Trains missing from options"
        assert "flight" in categories, "Flights missing from options"

        tempo_opts = [o for o in options if o["category"] == "tempo_traveller"]
        capacities = [o.get("capacity") for o in tempo_opts]
        assert 12 in capacities or 17 in capacities or 26 in capacities, "Expected standard tempo capacities"
        print(f"OK Transport search returned {total} options covering: {categories}")
        for t in tempo_opts:
            print(f"   - {t['title']} | {t['vehicle_type']} | {t['price_range']}")

def test_transport_route():
    req = urllib.request.Request(f"{BASE_URL}/api/transport/route?origin=Delhi&destination=Jaipur")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert "route" in data, "route key missing from response"
        route = data["route"]
        assert route["distance_km"] > 0
        assert route["geometry_geojson"]["type"] == "LineString"
        assert len(route["geometry_geojson"]["coordinates"]) > 1
        print(f"OK Route: {route['origin_name']} -> {route['destination_name']}, {route['distance_km']} km, {route['duration_str']}")

def test_gtfs_feeds():
    req = urllib.request.Request(f"{BASE_URL}/api/transport/feeds")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert "india_gtfs_feeds" in data, "india_gtfs_feeds missing"
        feeds = data["india_gtfs_feeds"]
        assert len(feeds) >= 5, f"Expected >=5 GTFS feeds, got {len(feeds)}"
        # Use whatever identifier key is present (id or agency_name)
        ids = [str(f.get("id", f.get("agency_name", ""))) for f in feeds]
        joined = " ".join(ids).upper()
        for agency in ["BMTC", "DTC", "BEST", "MTC", "KSRTC"]:
            assert agency in joined, f"Agency {agency} missing from GTFS feed IDs: {ids}"
        print(f"OK GTFS Feeds verified ({len(feeds)} feeds): {ids}")

def test_map_config():
    req = urllib.request.Request(f"{BASE_URL}/api/transport/map-config")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert "provider" in data
        assert "tile_url" in data
        print(f"OK Map config: provider={data['provider']}, tile_url={data['tile_url']}")

def test_voice_chat_endpoint():
    payload = json.dumps({
        "message": "What is the weather in Goa?",
        "history": []
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/voice/chat",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert "response" in data, "response key missing from voice chat"
        assert len(data["response"]) > 10, "Response too short"
        print(f"OK Voice chat API works. Response preview: {data['response'][:80]}...")

if __name__ == "__main__":
    print("=" * 60)
    print("YatraPilot AI - Transport Marketplace & Voice Verification")
    print("=" * 60)
    failures = []
    for test_fn in [test_homepage, test_transport_categories, test_transport_search,
                    test_transport_route, test_gtfs_feeds, test_map_config, test_voice_chat_endpoint]:
        try:
            test_fn()
        except Exception as e:
            print(f"FAIL {test_fn.__name__}: {e}")
            failures.append((test_fn.__name__, str(e)))

    print("=" * 60)
    if failures:
        print(f"RESULT: {len(failures)} test(s) FAILED:")
        for name, err in failures:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED!")
        sys.exit(0)
