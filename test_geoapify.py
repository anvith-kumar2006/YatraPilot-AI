
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ======================================
# CONFIGURATION
# ======================================

API_KEY = os.getenv("GEOAPIFY_API_KEY")

BASE_URL = "https://api.geoapify.com/v2/places"

# Bengaluru coordinates
LATITUDE = 12.9716
LONGITUDE = 77.5946

if not API_KEY:
    raise ValueError("GEOAPIFY_API_KEY missing in .env")


# ======================================
# FETCH TOURIST ATTRACTIONS
# ======================================

params = {
    "categories": "tourism.attraction",
    "filter": f"circle:{LONGITUDE},{LATITUDE},10000",
    "limit": 10,
    "apiKey": API_KEY
}

print("\n================================")
print(" YATRAPILOT AI - GEOAPIFY TEST")
print("================================")

try:
    response = requests.get(
        BASE_URL,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()
    places = data.get("features", [])

    print("\nSUCCESS: Geoapify API connected!")
    print("Places found:", len(places))

    for index, place in enumerate(places, start=1):
        details = place.get("properties", {})

        print(f"\n{index}. {details.get('name', 'Unnamed place')}")
        print("Address:", details.get("formatted", "Not available"))
        print("Categories:", details.get("categories", []))
        print("Coordinates:", details.get("lat"), details.get("lon"))

except requests.exceptions.HTTPError as error:
    print("\nHTTP ERROR:", response.status_code)

    if response.status_code in (401, 403):
        print("Check whether your API key is valid and enabled.")
    elif response.status_code == 429:
        print("API usage limit reached.")
    else:
        print(error)

except requests.exceptions.RequestException as error:
    print("\nNETWORK ERROR:", error)

except ValueError as error:
    print("\nRESPONSE ERROR:", error)

print("\nGEOAPIFY TEST COMPLETED")
