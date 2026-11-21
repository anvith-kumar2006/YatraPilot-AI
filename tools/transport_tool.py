"""
YatraPilot AI — Transportation Marketplace Tool
Exposes transportation discovery to Google Gemini agent as a live tool.
Supports all 7 categories: buses, trains, flights, taxis, rentals, tempo travellers, private coaches.
Connects with:
- Public road routing (OSRM / Geoapify)
- Open transit data (India GTFS / Mobility Database)
- Real registered private fleet providers (Neon PostgreSQL)
- Commercial partner adapters (IRCTC, Amadeus, Duffel, eTravelSmart, redBus)
"""

import json
import logging
from typing import Dict, Any, Optional
from integrations.transport import transport_marketplace

logger = logging.getLogger(__name__)


def discover_transportation(
    origin: str,
    destination: str,
    date: Optional[str] = None,
    category: Optional[str] = None,
    passengers: int = 1
) -> Dict[str, Any]:
    """
    Search across transportation marketplace providers for routes between origin and destination.
    
    Args:
        origin: Departure city or location (e.g. "Delhi", "Bengaluru", "Goa")
        destination: Arrival city or destination (e.g. "Jaipur", "Mysore", "Mumbai")
        date: Optional travel date in YYYY-MM-DD format
        category: Optional category filter: 'bus', 'train', 'flight', 'taxi', 'car_rental', 'tempo_traveller', 'private_coach', or 'all'
        passengers: Number of travellers (default 1)
        
    Returns:
        Structured dictionary with distance, driving duration, transit hubs, registered fleet providers, and commercial partner options.
    """
    try:
        data = transport_marketplace.search_marketplace(
            origin=origin,
            destination=destination,
            journey_date=date,
            category=category,
            passengers=passengers
        )

        route = data.get("route") or {}
        dist_km = route.get("distance_km", "N/A")
        dur_str = route.get("duration_str", "N/A")
        engine = route.get("routing_engine", "OSRM / MapTiler")

        options = data.get("options", [])

        # Categorize into Registered Fleet, Public Transit, and Commercial Partners
        registered_fleet = [o for o in options if "Neon DB" in o.get("source", "")]
        public_transit = [o for o in options if "GTFS" in o.get("source", "")]
        commercial_partners = [o for o in options if o.get("status") == "awaiting_partner_credentials"]
        standard_cabs = [o for o in options if "Chauffeur" in o.get("source", "") or "Rental" in o.get("source", "")]

        summary_lines = [
            f"### Transportation Discovery: {data['origin']['name']} ⇄ {data['destination']['name']}",
            f"- **Road Driving Distance**: ~{dist_km} km (Estimated duration: {dur_str} via {engine})",
            f"- **Passenger Count**: {passengers} traveller(s) · **Travel Date**: {date or 'Not specified (ask customer if needed)'}",
            f"- **Total Options Discovered**: {data['total_options']}",
            ""
        ]

        # 1. Registered Fleet Section (Neon PostgreSQL)
        if registered_fleet:
            summary_lines.append("#### 🚐 Certified Private Fleet Operators (Neon PostgreSQL DB):")
            for o in registered_fleet:
                contact = o.get("details", {}).get("contact_phone", "Verified Fleet")
                summary_lines.append(
                    f"- **{o['title']}** ({o['operator']})\n"
                    f"  - Vehicle: {o['vehicle_type']} (Capacity: {o.get('capacity', 'N/A')} seats)\n"
                    f"  - Fare: {o['price_range']}\n"
                    f"  - Contact: {contact} | Amenities: {', '.join(o.get('amenities', [])[:4])}\n"
                    f"  - Note: {o.get('notes', '')}"
                )
            summary_lines.append("")

        # 2. Road Cab / Rental Section
        if standard_cabs:
            summary_lines.append("#### 🚖 Outstation Cab & Rental Options:")
            for o in standard_cabs[:4]:
                summary_lines.append(f"- **{o['title']}**: {o['price_range']} (Capacity: {o.get('capacity', 'N/A')} seats)")
            summary_lines.append("")

        # 3. Public Transit Feeds Section
        if public_transit:
            summary_lines.append("#### 🚌 Public Transit & State Feeds (India GTFS):")
            for o in public_transit[:3]:
                summary_lines.append(f"- **{o['title']}** ({o['operator']}): {o['price_range']}")
            summary_lines.append("")

        # 4. Commercial Partner Networks (IRCTC, Amadeus, redBus, eTravelSmart)
        if commercial_partners:
            summary_lines.append("#### 🏢 Commercial Networks & Official Reservation Portals:")
            for o in commercial_partners[:4]:
                book_url = o.get("booking_url", "Official Portal")
                summary_lines.append(f"- **{o['title']}** ({o['operator']}) — Direct reservation at: {book_url}")
            summary_lines.append("")

        # Instructions for the AI
        summary_lines.extend([
            "**IMPORTANT TRAVEL AGENT INSTRUCTIONS**:",
            "1. NEVER claim a ticket is booked, seat is reserved, or fare is confirmed without direct provider confirmation.",
            "2. For Indian Railways, direct the customer to the official IRCTC portal (https://www.irctc.co.in).",
            "3. For flights, inform the customer that live airline fares depend on date/availability and provide official airline or Google Flights links.",
            "4. For Tempo Travellers (12/17/26 seaters) or outstation cabs, provide the registered operator details and standard per-km fare estimates.",
            "5. If travel date or passenger count is missing, politely ask the user to refine their itinerary."
        ])

        data["summary_text"] = "\n".join(summary_lines)
        return data

    except Exception as e:
        logger.error(f"Error in discover_transportation tool: {e}")
        return {
            "error": str(e),
            "origin": origin,
            "destination": destination,
            "options": []
        }
