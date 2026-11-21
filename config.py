import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-key-change-in-production")
    DEBUG = False
    TESTING = False
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # API Keys (never log these values)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
    MURF_API_KEY = os.getenv("MURF_API_KEY")
    
    # Agora
    AGORA_APP_ID = os.getenv("AGORA_APP_ID")
    AGORA_APP_CERTIFICATE = os.getenv("AGORA_APP_CERTIFICATE")
    AGORA_CUSTOMER_ID = os.getenv("AGORA_CUSTOMER_ID")
    AGORA_CUSTOMER_SECRET = os.getenv("AGORA_CUSTOMER_SECRET")
    
    # Murf Region
    MURF_REGION = os.getenv("MURF_REGION", "IN")
    
    # Transportation Marketplace APIs
    MAPTILER_API_KEY = os.getenv("MAPTILER_API_KEY")
    OSRM_ROUTING_URL = os.getenv("OSRM_ROUTING_URL", "https://router.project-osrm.org")
    NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
    INDIA_GTFS_API_URL = os.getenv("INDIA_GTFS_API_URL", "https://api.reclaim.city")
    RECLAIM_CITY_API_KEY = os.getenv("RECLAIM_CITY_API_KEY")
    MOBILITY_DATABASE_API_URL = os.getenv("MOBILITY_DATABASE_API_URL", "https://api.mobilitydatabase.org/v1")
    MOBILITY_DATABASE_API_KEY = os.getenv("MOBILITY_DATABASE_API_KEY")
    MOBILITY_DATABASE_REFRESH_TOKEN = os.getenv("MOBILITY_DATABASE_REFRESH_TOKEN")
    
    # eTravelSmart B2B Bus API
    ETRAVELSMART_ENABLED = os.getenv("ETRAVELSMART_ENABLED", "false").lower() == "true"
    ETRAVELSMART_API_URL = os.getenv("ETRAVELSMART_API_URL", "https://b2b.etravelsmart.com/bus/busApi.htm")
    ETRAVELSMART_USER_ID = os.getenv("ETRAVELSMART_USER_ID")
    ETRAVELSMART_PASSWORD = os.getenv("ETRAVELSMART_PASSWORD")
    ETRAVELSMART_API_KEY = os.getenv("ETRAVELSMART_API_KEY")
    
    # Future Provider Credentials (Placeholders)
    REDBUS_ENABLED = os.getenv("REDBUS_ENABLED", "false").lower() == "true"
    REDBUS_SEATSELLER_API_URL = os.getenv("REDBUS_SEATSELLER_API_URL", "https://api.seatseller.travel")
    REDBUS_SEATSELLER_KEY = os.getenv("REDBUS_SEATSELLER_KEY")
    IRCTC_ENABLED = os.getenv("IRCTC_ENABLED", "false").lower() == "true"
    IRCTC_PARTNER_API_URL = os.getenv("IRCTC_PARTNER_API_URL", "https://api.irctcpartner.com")
    IRCTC_PARTNER_KEY = os.getenv("IRCTC_PARTNER_KEY")
    AMADEUS_ENABLED = os.getenv("AMADEUS_ENABLED", "false").lower() == "true"
    AMADEUS_BASE_URL = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com/v2")
    AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
    AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
    DUFFEL_ENABLED = os.getenv("DUFFEL_ENABLED", "false").lower() == "true"
    DUFFEL_API_URL = os.getenv("DUFFEL_API_URL", "https://api.duffel.com")
    DUFFEL_API_KEY = os.getenv("DUFFEL_API_KEY")
    
    # Application Settings
    MAX_TOOL_ITERATIONS = 5  # Maximum times Gemini can call tools per turn
    AGORA_IDLE_TIMEOUT = 180  # Auto-stop after 180s of silence
    SESSION_STATE_POLL_INTERVAL = 1.5  # Frontend polls every 1.5 seconds
    
    # CORS Configuration - Restrict to specific origins
    # IMPORTANT: Do NOT use wildcard "*" in production
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5000,http://127.0.0.1:3000,http://127.0.0.1:5000"
    ).split(",")
    
    # Strip whitespace from origins
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS]


class DevelopmentConfig(Config):
    """Development environment"""
    DEBUG = True
    # Allow additional dev origins
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000",
        "http://localhost:8000",
    ]


class TestingConfig(Config):
    """Testing environment"""
    TESTING = True
    DATABASE_URL = "postgresql://test:test@localhost/yatrapilot_test"
    CORS_ORIGINS = ["http://localhost:5000"]


class ProductionConfig(Config):
    """Production environment"""
    DEBUG = False
    # Production should have CORS_ORIGINS set via environment variable
    # Example: CORS_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"

