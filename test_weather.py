
import openmeteo_requests
import pandas as pd
import requests_cache

from retry_requests import retry


# ==========================================
# 1. CONFIGURATION
# ==========================================

LATITUDE = 12.9716
LONGITUDE = 77.5946

# Cache responses for one hour
cache_session = requests_cache.CachedSession(
    ".cache",
    expire_after=3600
)

# Retry failed requests
retry_session = retry(
    cache_session,
    retries=5,
    backoff_factor=0.2
)

openmeteo = openmeteo_requests.Client(
    session=retry_session
)


# ==========================================
# 2. WEATHER API REQUEST
# ==========================================

url = "https://api.open-meteo.com/v1/forecast"

params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,

    "hourly": [
        "temperature_2m",
        "relative_humidity_2m",
        "apparent_temperature",
        "precipitation",
        "wind_speed_10m",
        "weather_code"
    ],

    "timezone": "auto",
    "forecast_days": 3
}


# ==========================================
# 3. FETCH WEATHER
# ==========================================

try:

    responses = openmeteo.weather_api(
        url,
        params=params
    )

    response = responses[0]

    print("\n================================")
    print(" YATRAPILOT AI WEATHER SERVICE")
    print("================================")

    print("Latitude:", response.Latitude())
    print("Longitude:", response.Longitude())
    print("Elevation:", response.Elevation(), "m")

    # ======================================
    # 4. PROCESS HOURLY DATA
    # ======================================

    hourly = response.Hourly()

    temperature = hourly.Variables(0).ValuesAsNumpy()
    humidity = hourly.Variables(1).ValuesAsNumpy()
    apparent_temperature = hourly.Variables(2).ValuesAsNumpy()
    precipitation = hourly.Variables(3).ValuesAsNumpy()
    wind_speed = hourly.Variables(4).ValuesAsNumpy()
    weather_code = hourly.Variables(5).ValuesAsNumpy()

    hourly_data = {

        "date": pd.date_range(
            start=pd.to_datetime(
                hourly.Time(),
                unit="s",
                utc=True
            ),
            end=pd.to_datetime(
                hourly.TimeEnd(),
                unit="s",
                utc=True
            ),
            freq=pd.Timedelta(
                seconds=hourly.Interval()
            ),
            inclusive="left"
        ),

        "temperature": temperature,
        "humidity": humidity,
        "feels_like": apparent_temperature,
        "precipitation": precipitation,
        "wind_speed": wind_speed,
        "weather_code": weather_code

    }

    dataframe = pd.DataFrame(hourly_data)

    # Convert timestamps to local timezone
    dataframe["date"] = (
        dataframe["date"]
        .dt.tz_convert(response.Timezone().decode("utf-8"))
    )

    print("\nSUCCESS: Weather data retrieved!")

    print("\nNext 10 hours forecast:")
    print(dataframe.head(10).to_string(index=False))

    # Save results
    dataframe.to_csv(
        "weather_forecast.csv",
        index=False
    )

    print("\nSaved: weather_forecast.csv")

except Exception as error:

    print("\nWEATHER API ERROR:")
    print(error)
