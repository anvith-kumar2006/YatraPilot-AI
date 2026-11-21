"""
YatraPilot AI - Flask Backend
AI-powered travel planning and recommendation platform

Architecture:
- Flask web server with CORS support
- Neon PostgreSQL database
- Gemini AI reasoning with tool calling
- Agora Conversational AI Engine for voice
- Open-Meteo for weather
- Geoapify for attractions

Routes:
- GET /health - Health check
- GET /api/weather - Weather forecast
- GET /api/places/search - Search attractions
- GET /api/places/nearby - Find nearby places
- POST /api/session/start - Start Agora session
- POST /api/session/stop - Stop Agora session
- GET /api/session/state - Get session state (polling)
- POST /api/llm/chat/completions - Custom LLM endpoint (SSE)
- POST /api/approve - HITL approval handler
- GET /api/trips - List saved trips
- GET /api/trips/<id> - Get trip details
"""

import os
import logging
import json
import uuid
import base64
from datetime import datetime
from flask import Flask, request, jsonify, Response, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment early
load_dotenv()

from config import Config
from database.db import init_db, get_db
from integrations.agora import create_agora_client
from integrations.gemini import create_gemini_agent
from integrations.travel_apis import create_weather_service, create_places_service
from integrations.murf import generate_speech, get_initial_greeting_audio, clean_text_for_speech
from tools.travel_tools import (
    get_weather,
    search_attractions,
    estimate_trip_budget,
    generate_itinerary,
    save_trip,
    update_itinerary,
    discover_transportation
)
from integrations.transport import transport_marketplace

# ============================================================================
# SETUP
# ============================================================================

app = Flask(__name__)
app.config.from_object(Config)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure CORS with allowed origins from config
cors_config = {
    "origins": app.config.get("CORS_ORIGINS", ["http://localhost:3000"]),
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
    "supports_credentials": False,
    "max_age": 3600
}

CORS(app, resources={r"/api/*": cors_config}, origins=cors_config["origins"])

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
@app.before_request
def setup_db():
    """Initialize database on first request."""
    if not hasattr(app, 'db_initialized'):
        try:
            if init_db():
                app.db_initialized = True
                logger.info("✓ Database initialized")
        except Exception as e:
            logger.error(f"✗ Database initialization failed: {e}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_string(value, field_name, max_length=100, required=True):
    """Validate string input."""
    if required and (not value or not isinstance(value, str)):
        return False, f"{field_name} must be a non-empty string"
    
    if value and len(str(value)) > max_length:
        return False, f"{field_name} exceeds maximum length of {max_length}"
    
    return True, ""


def validate_integer(value, field_name, min_val=None, max_val=None, required=True):
    """Validate integer input."""
    if required and not isinstance(value, int):
        return False, f"{field_name} must be an integer"
    
    if value is not None:
        if min_val is not None and value < min_val:
            return False, f"{field_name} must be >= {min_val}"
        if max_val is not None and value > max_val:
            return False, f"{field_name} must be <= {max_val}"
    
    return True, ""


def validate_float(value, field_name, min_val=None, max_val=None, required=True):
    """Validate float input."""
    if required and not isinstance(value, (int, float)):
        return False, f"{field_name} must be a number"
    
    if value is not None:
        if min_val is not None and value < min_val:
            return False, f"{field_name} must be >= {min_val}"
        if max_val is not None and value > max_val:
            return False, f"{field_name} must be <= {max_val}"
    
    return True, ""


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    try:
        db = get_db()
        if db.test_connection():
            return jsonify({
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "environment": os.getenv("FLASK_ENV", "development")
            }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================
# WEATHER ENDPOINT (Priority 3 - NEW)
# ============================================================================

@app.route('/api/weather', methods=['GET'])
def weather():
    """
    Get weather for a destination.
    
    Query parameters:
    - city: City name (required)
    - lat: Latitude (optional, overrides city)
    - lon: Longitude (optional, overrides city)
    
    Returns:
        Weather forecast data from Open-Meteo
    """
    try:
        city = request.args.get('city', '').strip()
        lat_str = request.args.get('lat', '').strip()
        lon_str = request.args.get('lon', '').strip()
        
        # Validate inputs
        if not city and not (lat_str and lon_str):
            return jsonify({
                "error": "Missing required parameters. Provide 'city' OR both 'lat' and 'lon'"
            }), 400
        
        # If coordinates provided, validate them
        if lat_str and lon_str:
            try:
                lat = float(lat_str)
                lon = float(lon_str)
                
                if not -90 <= lat <= 90:
                    return jsonify({"error": "Latitude must be between -90 and 90"}), 400
                if not -180 <= lon <= 180:
                    return jsonify({"error": "Longitude must be between -180 and 180"}), 400
                
                # Call tool with coordinates
                result = get_weather(destination=f"{lat},{lon}")
            except ValueError:
                return jsonify({"error": "Invalid coordinate format"}), 400
        else:
            # Validate city name
            is_valid, error = validate_string(city, "city", max_length=100)
            if not is_valid:
                return jsonify({"error": error}), 400
            
            # Call tool with city
            result = get_weather(destination=city)
        
        if result.get("status") == "error":
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Weather endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PLACES SEARCH ENDPOINT (Priority 3 - NEW)
# ============================================================================

@app.route('/api/places/search', methods=['GET'])
def places_search():
    """
    Search for attractions at a location.
    
    Query parameters:
    - city: City name (required)
    - lat: Latitude (optional)
    - lon: Longitude (optional)
    
    Returns:
        List of attractions from Geoapify
    """
    try:
        city = request.args.get('city', '').strip()
        lat_str = request.args.get('lat', '').strip()
        lon_str = request.args.get('lon', '').strip()
        
        # Validate inputs
        if not city:
            return jsonify({"error": "Missing required parameter: city"}), 400
        
        is_valid, error = validate_string(city, "city", max_length=100)
        if not is_valid:
            return jsonify({"error": error}), 400
        
        # If coordinates provided, validate them
        lat = None
        lon = None
        if lat_str and lon_str:
            try:
                lat = float(lat_str)
                lon = float(lon_str)
                
                if not -90 <= lat <= 90:
                    return jsonify({"error": "Latitude must be between -90 and 90"}), 400
                if not -180 <= lon <= 180:
                    return jsonify({"error": "Longitude must be between -180 and 180"}), 400
            except ValueError:
                return jsonify({"error": "Invalid coordinate format"}), 400
        
        # Call tool
        result = search_attractions(
            destination=city,
            latitude=lat,
            longitude=lon
        )
        
        if result.get("status") == "error":
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Places search endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PLACES NEARBY ENDPOINT (Priority 3 - NEW)
# ============================================================================

@app.route('/api/places/nearby', methods=['GET'])
def places_nearby():
    """
    Find attractions near specific coordinates.
    
    Query parameters:
    - lat: Latitude (required)
    - lon: Longitude (required)
    - radius: Search radius in meters (optional, default 10000, max 50000)
    
    Returns:
        List of nearby attractions from Geoapify
    """
    try:
        lat_str = request.args.get('lat', '').strip()
        lon_str = request.args.get('lon', '').strip()
        radius_str = request.args.get('radius', '10000').strip()
        
        # Validate latitude and longitude (required)
        if not lat_str or not lon_str:
            return jsonify({
                "error": "Missing required parameters: lat and lon"
            }), 400
        
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            radius = int(radius_str)
            
            if not -90 <= lat <= 90:
                return jsonify({"error": "Latitude must be between -90 and 90"}), 400
            if not -180 <= lon <= 180:
                return jsonify({"error": "Longitude must be between -180 and 180"}), 400
            if radius < 100 or radius > 50000:
                return jsonify({"error": "Radius must be between 100 and 50000 meters"}), 400
            
        except ValueError:
            return jsonify({"error": "Invalid coordinate or radius format"}), 400
        
        # Get places service
        places_service = create_places_service()
        
        # Search with dynamic radius
        attractions = places_service.search_attractions(
            latitude=lat,
            longitude=lon,
            radius_meters=radius,
            limit=20
        )
        
        return jsonify({
            "status": "success",
            "latitude": lat,
            "longitude": lon,
            "radius_meters": radius,
            "count": len(attractions),
            "attractions": attractions,
            "message": f"Found {len(attractions)} attractions within {radius}m"
        }), 200
        
    except Exception as e:
        logger.error(f"Places nearby endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# SESSION LIFECYCLE ENDPOINTS
# ============================================================================

@app.route('/api/session/start', methods=['POST'])
def start_session():
    """
    Start an Agora Conversational AI session.
    
    Request: {"user_uid": 1002}
    Response: {
        "app_id": "...",
        "channel": "voicetrip_xxx",
        "token": "...",
        "uid": 1002,
        "agent_id": "..."
    }
    """
    try:
        data = request.get_json() or {}
        user_uid = data.get("user_uid", 1000)
        
        # Validate user_uid
        is_valid, error = validate_integer(user_uid, "user_uid", min_val=1, max_val=2147483647)
        if not is_valid:
            return jsonify({"error": error}), 400
        
        # Generate unique channel name
        channel = f"yatra_{uuid.uuid4().hex[:8]}"
        
        # Create Agora client and start agent
        agora = create_agora_client()
        
        # Build LLM endpoint from actual request URL
        # If PUBLIC_URL is set (e.g. ngrok tunnel), use that for the Agora callback
        # so Agora cloud can reach the LLM endpoint
        public_base = os.getenv("PUBLIC_URL", "").rstrip("/")
        if not public_base:
            # Fallback to request URL root (works only if server is publicly accessible)
            public_base = request.url_root.rstrip("/")

        llm_endpoint = f"{public_base}/api/llm/chat/completions"
        # Use a secure internal key for LLM calls from Agora
        llm_internal_key = os.getenv("FLASK_SECRET_KEY", "yatra-internal-llm")

        session_info = agora.start_agent(
            channel=channel,
            llm_api_key=llm_internal_key,
            llm_api_endpoint=llm_endpoint,
            murf_api_key=os.getenv("MURF_API_KEY"),
            user_uid=user_uid,
            voice_id="Matthew"
        )
        
        logger.info(f"✓ Session started: {channel}")
        
        return jsonify(session_info), 200
        
    except Exception as e:
        logger.error(f"Start session error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/session/stop', methods=['POST'])
def stop_session():
    """
    Stop an Agora agent session.
    
    Request: {"agent_id": "..."}
    Response: {"status": "success"}
    """
    try:
        data = request.get_json() or {}
        agent_id = data.get("agent_id")
        channel = data.get("channel")
        
        if not agent_id:
            return jsonify({"error": "Missing agent_id"}), 400
        
        # Validate agent_id format (non-empty string)
        is_valid, error = validate_string(agent_id, "agent_id", max_length=256)
        if not is_valid:
            return jsonify({"error": error}), 400
        
        # Stop Agora agent
        agora = create_agora_client()
        agora.stop_agent(agent_id)
        
        # Clear session state
        if channel:
            db = get_db()
            db.clear_session_state(channel)
        
        logger.info(f"✓ Session stopped: {agent_id}")
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Stop session error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/session/state', methods=['GET'])
def get_session_state():
    """
    Get current session state (for UI polling).
    
    Query params: ?channel=voicetrip_xxx
    Response: {
        "active_itinerary": {...},
        "pending_approval": {...},
        "last_tools": [...],
        "transcript": [...]
    }
    """
    try:
        channel = request.args.get("channel")
        if not channel:
            return jsonify({"error": "Missing channel param"}), 400
        
        # Validate channel format
        is_valid, error = validate_string(channel, "channel", max_length=100)
        if not is_valid:
            return jsonify({"error": error}), 400
        
        db = get_db()
        
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT active_itinerary_json, pending_approval_json, last_tools_json, transcript_json FROM session_state WHERE channel_name = %s",
                (channel,)
            )
            row = cursor.fetchone()
        
        if not row:
            return jsonify({
                "channel": channel,
                "active_itinerary": None,
                "pending_approval": None,
                "last_tools": [],
                "transcript": []
            }), 200
        
        active_iter, pending_app, last_tools, transcript = row
        
        return jsonify({
            "channel": channel,
            "active_itinerary": json.loads(active_iter) if active_iter else None,
            "pending_approval": json.loads(pending_app) if pending_app else None,
            "last_tools": json.loads(last_tools) if last_tools else [],
            "transcript": json.loads(transcript) if transcript else []
        }), 200
        
    except Exception as e:
        logger.error(f"Get session state error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# CUSTOM LLM ENDPOINT (for Agora)
# ============================================================================

@app.route('/api/llm/chat/completions', methods=['POST'])
def llm_chat_completions():
    """
    OpenAI-compatible SSE endpoint for Agora Custom LLM.
    
    Agora calls this with: {
        "messages": [{"role": "user", "content": "..."}],
        ...
    }
    
    Returns: text/event-stream with SSE chunks
    """
    try:
        data = request.get_json() or {}
        messages = data.get("messages", [])
        
        if not messages:
            return jsonify({"error": "No messages"}), 400
        
        if not isinstance(messages, list):
            return jsonify({"error": "messages must be a list"}), 400
        
        # Create Gemini agent
        agent = create_gemini_agent()
        
        # Register tools
        agent.register_tool(
            "get_weather",
            get_weather,
            "Get weather forecast for a destination",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD format"}
                },
                "required": ["destination"]
            }
        )
        
        agent.register_tool(
            "search_attractions",
            search_attractions,
            "Search for tourist attractions",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "preferences": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["destination"]
            }
        )
        
        agent.register_tool(
            "estimate_trip_budget",
            estimate_trip_budget,
            "Estimate trip budget",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "duration_days": {"type": "integer"},
                    "travellers": {"type": "integer"},
                    "accommodation_level": {"type": "string"}
                },
                "required": ["destination", "duration_days", "travellers"]
            }
        )
        
        agent.register_tool(
            "generate_itinerary",
            generate_itinerary,
            "Generate a day-by-day itinerary",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "duration_days": {"type": "integer"},
                    "preferences": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["destination", "start_date", "duration_days"]
            }
        )
        
        agent.register_tool(
            "save_trip",
            save_trip,
            "Save trip to database (requires user confirmation)",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "start_date": {"type": "string"},
                    "duration_days": {"type": "integer"},
                    "budget_amount": {"type": "number"},
                    "itinerary_json": {"type": "string"},
                    "user_confirmed": {"type": "boolean"}
                },
                "required": ["destination", "start_date", "duration_days", "budget_amount", "itinerary_json"]
            }
        )
        
        agent.register_tool(
            "update_itinerary",
            update_itinerary,
            "Update an existing trip (requires user confirmation)",
            {
                "properties": {
                    "trip_id": {"type": "integer"},
                    "changes": {"type": "object"},
                    "user_confirmed": {"type": "boolean"}
                },
                "required": ["trip_id", "changes"]
            }
        )
        
        # Get response from Gemini
        system_prompt = """You are an intelligent travel concierge assistant. You help users plan amazing trips.

Rules:
- Use tools to gather real information (weather, attractions, budget)
- Never invent data; always use tool results
- Be concise and natural in your responses
- If user asks to save/modify a trip, confirm the action
- Speak naturally, as if talking to a friend"""
        
        response_text = agent.chat_with_tools(
            messages,
            system_prompt,
            max_iterations=5
        )
        
        # Stream response as SSE
        def generate():
            yield f"data: {json.dumps({'choices': [{'delta': {'content': response_text}}]})}\n\n"
            yield "data: [DONE]\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream'
        )
        
    except Exception as e:
        logger.error(f"LLM endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# APPROVAL ENDPOINT (HITL)
# ============================================================================

@app.route('/api/approve', methods=['POST'])
def approve_action():
    """
    Approve or reject a pending human-in-the-loop action.
    
    Request: {
        "channel": "voicetrip_xxx",
        "action_id": "save_trip_123",
        "approved": true,
        "action": "save_trip",
        "trip_data": {...}
    }
    """
    try:
        data = request.get_json() or {}
        channel = data.get("channel")
        approved = data.get("approved", False)
        action = data.get("action")
        
        if not channel or not action:
            return jsonify({"error": "Missing required fields: channel, action"}), 400
        
        # Validate inputs
        is_valid, error = validate_string(channel, "channel", max_length=100)
        if not is_valid:
            return jsonify({"error": error}), 400
        
        is_valid, error = validate_string(action, "action", max_length=50)
        if not is_valid:
            return jsonify({"error": error}), 400
        
        if not isinstance(approved, bool):
            return jsonify({"error": "approved must be a boolean"}), 400
        
        # Handle approval
        db = get_db()
        
        if action == "save_trip" and approved:
            trip_data = data.get("trip_data", {})
            trip_id = save_trip(
                destination=trip_data.get("destination"),
                start_date=trip_data.get("start_date"),
                duration_days=trip_data.get("duration_days"),
                budget_amount=trip_data.get("budget_amount"),
                itinerary_json=trip_data.get("itinerary_json", "{}"),
                user_confirmed=True,
                channel_name=channel
            )
            
            logger.info(f"✓ Approved: save_trip")
            
            return jsonify({
                "status": "approved",
                "action": action,
                "result": trip_id
            }), 200
        
        else:
            logger.info(f"✓ Rejected or processed: {action}")
            
            return jsonify({
                "status": "handled",
                "action": action
            }), 200
        
    except Exception as e:
        logger.error(f"Approval handler error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TRIP MANAGEMENT ENDPOINTS
# ============================================================================

@app.route('/api/trips', methods=['GET'])
def get_trips():
    """Get all saved trips."""
    try:
        db = get_db()
        
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT id, destination, start_date, duration_days, budget_amount, status, created_at FROM trips ORDER BY created_at DESC LIMIT 50"
            )
            rows = cursor.fetchall()
        
        trips = [
            {
                "id": row[0],
                "destination": row[1],
                "start_date": row[2],
                "duration_days": row[3],
                "budget_amount": row[4],
                "status": row[5],
                "created_at": row[6].isoformat() if row[6] else None
            }
            for row in rows
        ]
        
        return jsonify({"trips": trips}), 200
        
    except Exception as e:
        logger.error(f"Get trips error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    """Get a specific trip by ID."""
    try:
        # Validate trip_id
        if trip_id <= 0:
            return jsonify({"error": "trip_id must be positive"}), 400
        
        db = get_db()
        
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM trips WHERE id = %s",
                (trip_id,)
            )
            row = cursor.fetchone()
        
        if not row:
            return jsonify({"error": "Trip not found"}), 404
        
        # Map columns
        columns = [
            "id", "channel_name", "destination", "start_date", "duration_days",
            "travellers", "budget_amount", "currency", "preferences_json",
            "weather_summary_json", "attractions_json", "itinerary_json",
            "status", "created_at", "updated_at"
        ]
        
        trip = dict(zip(columns, row))
        
        # Parse JSON fields
        trip["preferences"] = json.loads(trip["preferences_json"]) if trip["preferences_json"] else None
        trip["weather_summary"] = json.loads(trip["weather_summary_json"]) if trip["weather_summary_json"] else None
        trip["attractions"] = json.loads(trip["attractions_json"]) if trip["attractions_json"] else None
        trip["itinerary"] = json.loads(trip["itinerary_json"]) if trip["itinerary_json"] else None
        
        # Convert datetime
        trip["created_at"] = trip["created_at"].isoformat() if trip["created_at"] else None
        trip["updated_at"] = trip["updated_at"].isoformat() if trip["updated_at"] else None
        
        return jsonify(trip), 200
        
    except Exception as e:
        logger.error(f"Get trip error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================



# ============================================================================
# FRONTEND ROUTES (Phase 3)
# ============================================================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Text chat endpoint — powers the chat UI.
    Accepts a message + optional history array, calls Gemini with tools.
    """
    try:
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            return jsonify({"error": "Message required"}), 400

        # Sanitize and validate history
        clean_history = []
        for entry in (history or []):
            if isinstance(entry, dict) and entry.get("role") in ("user", "assistant") and entry.get("content"):
                clean_history.append({
                    "role": entry["role"],
                    "content": str(entry["content"])[:4000]  # limit per message
                })

        # Build full messages list: history + current message
        messages = clean_history + [{"role": "user", "content": message}]

        # Create Gemini agent with all travel tools
        agent = create_gemini_agent()

        agent.register_tool(
            "get_weather",
            get_weather,
            "Get current weather forecast for a destination city",
            {
                "properties": {
                    "destination": {"type": "string", "description": "City name"},
                    "date": {"type": "string", "description": "YYYY-MM-DD format (optional)"}
                },
                "required": ["destination"]
            }
        )

        agent.register_tool(
            "search_attractions",
            search_attractions,
            "Search for tourist attractions and places of interest",
            {
                "properties": {
                    "destination": {"type": "string", "description": "City name"},
                    "preferences": {"type": "array", "items": {"type": "string"}, "description": "Interest types"}
                },
                "required": ["destination"]
            }
        )

        agent.register_tool(
            "estimate_trip_budget",
            estimate_trip_budget,
            "Estimate a trip budget with breakdown by accommodation, meals, activities and transport",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "duration_days": {"type": "integer"},
                    "travellers": {"type": "integer"},
                    "accommodation_level": {"type": "string", "description": "budget | mid | luxury"}
                },
                "required": ["destination", "duration_days", "travellers"]
            }
        )

        agent.register_tool(
            "generate_itinerary",
            generate_itinerary,
            "Generate a detailed day-by-day travel itinerary",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "duration_days": {"type": "integer"},
                    "preferences": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["destination", "start_date", "duration_days"]
            }
        )

        agent.register_tool(
            "save_trip",
            save_trip,
            "Save a trip to the database (requires user confirmation)",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "start_date": {"type": "string"},
                    "duration_days": {"type": "integer"},
                    "budget_amount": {"type": "number"},
                    "itinerary_json": {"type": "string"},
                    "user_confirmed": {"type": "boolean"}
                },
                "required": ["destination", "start_date", "duration_days", "budget_amount", "itinerary_json"]
            }
        )

        agent.register_tool(
            "discover_transportation",
            discover_transportation,
            "Discover transportation options (buses, trains, flights, taxis, car rentals, tempo travellers, private coaches) and road distance between cities",
            {
                "properties": {
                    "origin": {"type": "string", "description": "Departure city or location"},
                    "destination": {"type": "string", "description": "Arrival city or destination"},
                    "date": {"type": "string", "description": "Travel date YYYY-MM-DD (optional)"},
                    "category": {"type": "string", "description": "Optional category filter: bus | train | flight | taxi | car_rental | tempo_traveller | private_coach | all"},
                    "passengers": {"type": "integer", "description": "Number of travellers"}
                },
                "required": ["origin", "destination"]
            }
        )

        system_prompt = """You are YatraPilot AI, a premium intelligent travel concierge.

Your mission: Help users discover destinations, plan complete itineraries, understand weather, find attractions, estimate budgets, and discover transportation options.

Guidelines:
- Use your tools (get_weather, search_attractions, estimate_trip_budget, generate_itinerary, save_trip, discover_transportation) to get real data — never invent numbers
- When users ask about travel between cities, how to reach a place, trains (Vande Bharat, Rajdhani), buses, taxis, car rentals, or tempo travellers for groups, use discover_transportation to find real route options and distances
- Be warm, enthusiastic and conversational — like an expert friend who travels often
- Format responses with clear structure using **bold** headings, bullet points and line breaks
- When generating an itinerary, make it detailed, realistic and specific to the destination
- For budget estimates, always specify the currency (₹ INR) and include a breakdown
- If someone asks to save a trip, use save_trip with user_confirmed=False first to trigger the approval flow
- Keep responses focused and practical — no unnecessary filler text
- If you don't have enough information (e.g. no dates), ask a clarifying question

Always use markdown-compatible formatting in your replies."""

        response_text = agent.chat_with_tools(
            messages,
            system_prompt,
            max_iterations=5
        )

        return jsonify({"response": response_text}), 200

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/voice/greeting", methods=["GET"])
def voice_greeting():
    """
    Returns the initial spoken greeting generated by Murf Falcon 2.1 as MP3 audio.
    """
    try:
        audio_bytes = get_initial_greeting_audio()
        return Response(audio_bytes, mimetype="audio/mpeg")
    except Exception as e:
        logger.error(f"Voice greeting error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/tts/generate", methods=["POST"])
def tts_generate():
    """
    Direct TTS generation endpoint using Murf Falcon 2.1.
    """
    try:
        data = request.get_json() or {}
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "Text is required"}), 400

        audio_bytes = generate_speech(text)
        return Response(audio_bytes, mimetype="audio/mpeg")
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/voice/chat", methods=["POST"])
def voice_chat():
    """
    Voice-first chat endpoint:
    1. Processes user query with Gemini travel agent (with live tools).
    2. Instructs Gemini to produce a concise, conversational spoken travel response.
    3. Converts response to audio via Murf Falcon 2.1.
    4. Returns JSON with response text and base64-encoded MP3 audio.
    """
    try:
        data = request.get_json(silent=True) or {}
        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            return jsonify({"error": "Message required"}), 400

        # Sanitize history
        clean_history = []
        for entry in (history or []):
            if isinstance(entry, dict) and entry.get("role") in ("user", "assistant") and entry.get("content"):
                clean_history.append({
                    "role": entry["role"],
                    "content": str(entry["content"])[:2000]
                })

        messages = clean_history + [{"role": "user", "content": message}]

        agent = create_gemini_agent()
        agent.register_tool(
            "get_weather",
            get_weather,
            "Get current weather forecast for a destination city",
            {
                "properties": {
                    "destination": {"type": "string", "description": "City name"},
                    "date": {"type": "string", "description": "YYYY-MM-DD format (optional)"}
                },
                "required": ["destination"]
            }
        )
        agent.register_tool(
            "search_attractions",
            search_attractions,
            "Search for tourist attractions and places of interest",
            {
                "properties": {
                    "destination": {"type": "string", "description": "City name"},
                    "preferences": {"type": "array", "items": {"type": "string"}, "description": "Interest types"}
                },
                "required": ["destination"]
            }
        )
        agent.register_tool(
            "estimate_trip_budget",
            estimate_trip_budget,
            "Estimate a trip budget with breakdown by accommodation, meals, activities and transport",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "duration_days": {"type": "integer"},
                    "travellers": {"type": "integer"},
                    "accommodation_level": {"type": "string", "description": "budget | mid | luxury"}
                },
                "required": ["destination", "duration_days", "travellers"]
            }
        )
        agent.register_tool(
            "generate_itinerary",
            generate_itinerary,
            "Generate a detailed day-by-day travel itinerary",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "duration_days": {"type": "integer"},
                    "preferences": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["destination", "start_date", "duration_days"]
            }
        )

        agent.register_tool(
            "discover_transportation",
            discover_transportation,
            "Discover transportation options (buses, trains, flights, taxis, car rentals, tempo travellers, private coaches) and road distance between cities",
            {
                "properties": {
                    "origin": {"type": "string", "description": "Departure city or location"},
                    "destination": {"type": "string", "description": "Arrival city or destination"},
                    "date": {"type": "string", "description": "Travel date YYYY-MM-DD (optional)"},
                    "category": {"type": "string", "description": "Optional category filter: bus | train | flight | taxi | car_rental | tempo_traveller | private_coach | all"},
                    "passengers": {"type": "integer", "description": "Number of travellers"}
                },
                "required": ["origin", "destination"]
            }
        )

        voice_system_prompt = """You are YatraPilot AI, an intelligent, charming travel concierge speaking directly to the user.
Your mission: Answer the user's travel query warmly and helpfully.
IMPORTANT VOICE GUIDELINES:
- Since your response is spoken aloud via Murf audio, do NOT use markdown formatting (no asterisks, no hash signs, no bullet points, no tables, no emojis).
- Keep your reply concise, conversational, and pleasant to listen to (typically 2 to 4 sentences).
- When asked about transportation, routes, trains, buses, cabs, tempo travellers, or driving distance, use discover_transportation to provide accurate numbers and travel options.
- Speak in smooth, natural English as an enthusiastic travel expert."""

        response_text = agent.chat_with_tools(
            messages,
            voice_system_prompt,
            max_iterations=5
        )

        # Generate audio using Murf Falcon
        logger.info(f"Generating Murf audio for voice response: {response_text[:80]}...")
        audio_bytes = generate_speech(response_text)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return jsonify({
            "response": response_text,
            "audio_base64": audio_b64
        }), 200

    except Exception as e:
        logger.error(f"Voice chat endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TRANSPORTATION MARKETPLACE & DISCOVERY ENDPOINTS
# ============================================================================

@app.route("/api/transport/categories", methods=["GET"])
def get_transport_categories():
    """Returns supported transportation categories and metadata."""
    try:
        categories = transport_marketplace.get_supported_categories()
        return jsonify({"categories": categories}), 200
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/transport/providers", methods=["GET"])
def get_transport_providers():
    """Returns directory of all integrated transportation providers and credential status."""
    try:
        providers = transport_marketplace.get_providers_directory()
        return jsonify({"providers": providers}), 200
    except Exception as e:
        logger.error(f"Error fetching provider directory: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/transport/search", methods=["POST"])
def search_transportation_marketplace():
    """
    Search transportation options across all 7 categories:
    buses, trains, flights, taxis, car rentals, tempo travellers, and private coaches.
    Includes road distance and route geometry via MapTiler / OSRM.
    """
    try:
        data = request.get_json(silent=True) or {}
        origin = data.get("origin", "").strip()
        destination = data.get("destination", "").strip()
        journey_date = data.get("journey_date")
        category = data.get("category", "all")
        passengers = int(data.get("passengers", 1))

        if not origin or not destination:
            return jsonify({"error": "Origin and destination are required"}), 400

        result = transport_marketplace.search_marketplace(
            origin=origin,
            destination=destination,
            journey_date=journey_date,
            category=category,
            passengers=passengers
        )
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Transportation search error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/transport/route", methods=["GET"])
def get_transport_route():
    """Calculates route, driving distance, duration, and GeoJSON geometry via MapTiler/OSRM."""
    try:
        origin = request.args.get("origin", "Delhi").strip()
        destination = request.args.get("destination", "Agra").strip()

        data = transport_marketplace.search_marketplace(
            origin=origin,
            destination=destination,
            category="all"
        )
        return jsonify({
            "origin": data.get("origin"),
            "destination": data.get("destination"),
            "route": data.get("route"),
            "transit_hubs": data.get("transit_hubs"),
            "map_config": data.get("map_config")
        }), 200

    except Exception as e:
        logger.error(f"Route calculation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/transport/feeds", methods=["GET"])
def get_transit_feeds():
    """Returns available India GTFS datasets and Mobility Database discovery feeds."""
    try:
        india_feeds = transport_marketplace.india_gtfs.get_available_feeds()
        mobility_feeds = transport_marketplace.mobility_db.discover_feeds()
        return jsonify({
            "india_gtfs_feeds": india_feeds,
            "mobility_database_feeds": mobility_feeds,
            "disclaimer": "Public transit datasets are informational schedules provided under respective open data licenses. No ticket-booking claim is made from GTFS data."
        }), 200

    except Exception as e:
        logger.error(f"Transit feeds lookup error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/transport/map-config", methods=["GET"])
def get_map_config():
    """Returns MapTiler or OpenStreetMap client configuration for interactive maps."""
    return jsonify(transport_marketplace.maptiler.get_map_config()), 200


@app.route("/api/transport/availability", methods=["GET"])
def get_transport_availability():
    """
    Returns the real-time transportation integration availability matrix:
    READY, PUBLIC, MISSING_CREDENTIALS, PARTNER_REQUIRED, and UNAVAILABLE.
    """
    try:
        matrix = transport_marketplace.get_availability_matrix()
        return jsonify(matrix), 200
    except Exception as e:
        logger.error(f"Error evaluating availability matrix: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/transport/registered-providers", methods=["GET"])
def get_registered_fleet_providers():
    """Returns active verified private transport providers stored in Neon PostgreSQL."""
    try:
        from database.transport_db import get_registered_providers
        category = request.args.get("category")
        region = request.args.get("region")
        providers = get_registered_providers(category=category, region=region)
        return jsonify({
            "status": "success",
            "count": len(providers),
            "providers": providers
        }), 200
    except Exception as e:
        logger.error(f"Error fetching registered providers: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/transport/providers/register", methods=["POST"])
def register_transport_provider():
    """Registers a genuine private transport provider into Neon PostgreSQL."""
    try:
        from database.transport_db import register_new_provider
        data = request.get_json(silent=True) or {}
        if not data.get("provider_name") or not data.get("category"):
            return jsonify({"error": "provider_name and category are required"}), 400

        new_id = register_new_provider(data)
        if new_id:
            return jsonify({
                "status": "success",
                "message": f"Provider '{data.get('provider_name')}' successfully registered",
                "id": new_id
            }), 201
        else:
            return jsonify({"error": "Failed to store provider in database"}), 500
    except Exception as e:
        logger.error(f"Error registering provider: {e}")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    logger.info("Starting YatraPilot AI Flask server...")
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development',
        threaded=True  # Enable threading for concurrent requests
    )



# ============================================================================
