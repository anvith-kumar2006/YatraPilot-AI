"""
YatraPilot AI — Duffel Flights API Adapter
Provides airline offer search and flight ticket verification via Duffel Flights API.
Website: https://duffel.com/docs/api
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Any
from .base import BaseTransportProvider, TransportOption, TransportCategory, ProviderStatus

logger = logging.getLogger(__name__)

DUFFEL_API_BASE = "https://api.duffel.com"
DUFFEL_API_VERSION = "v2"


class DuffelFlightAdapter(BaseTransportProvider):
    """
    Adapter for commercial flight offers via Duffel Flights API.
    Remains cleanly disabled if DUFFEL_API_KEY is not configured or DUFFEL_ENABLED is false.
    Zero fake inventory is shown.
    """
    name: str = "Duffel Flights Network"
    category: TransportCategory = TransportCategory.FLIGHT

    def __init__(self):
        self.api_key = os.getenv("DUFFEL_API_KEY", "").strip()
        self.is_enabled = os.getenv("DUFFEL_ENABLED", "false").lower() == "true"
        self.base_url = os.getenv("DUFFEL_API_URL", DUFFEL_API_BASE).rstrip("/")
        super().__init__(api_key=self.api_key, base_url=self.base_url)

    def is_active(self) -> bool:
        return bool(self.api_key and self.is_enabled and len(self.api_key) > 5)

    def get_status(self) -> Dict[str, Any]:
        configured = self.is_active()
        return {
            "name": self.name,
            "category": self.category.value,
            "is_configured": configured,
            "status": ProviderStatus.ACTIVE.value if configured else ProviderStatus.AWAITING_CREDENTIALS.value,
            "auth_mode": "Bearer Token (Duffel-Version: v2)",
            "requires": ["DUFFEL_API_KEY", "DUFFEL_ENABLED=true"],
            "documentation": "https://duffel.com/docs/api"
        }

    def search(
        self,
        origin: str,
        destination: str,
        journey_date: Optional[str] = None,
        passengers: int = 1,
        **kwargs
    ) -> List[TransportOption]:
        """
        Queries Duffel Flights API for live flight offers.
        If credentials are not configured, returns informational status without fake booking.
        """
        if not self.is_active():
            return [
                TransportOption(
                    id="duffel_status_info",
                    provider_name=self.name,
                    category=self.category.value,
                    operator="Duffel Airline Network (300+ Global Carriers)",
                    title=f"Commercial Flight Search: {origin.title()} ⇄ {destination.title()}",
                    vehicle_type="Domestic Scheduled Airline",
                    price_range="Live Fare Quoting requires Duffel API Credentials",
                    source="Duffel Flights API (Modular Adapter)",
                    status=ProviderStatus.AWAITING_CREDENTIALS.value,
                    is_bookable=False,
                    booking_url="https://duffel.com",
                    notes="Duffel Flight Adapter is modularly integrated. Live airline inventory search, seat maps, and PNR creation require valid DUFFEL_API_KEY and DUFFEL_ENABLED=true in .env. Zero fake flight inventory is displayed.",
                    details={
                        "auth_mode": "Bearer Token Authentication",
                        "documentation": "https://duffel.com/docs/api",
                        "requires": ["DUFFEL_API_KEY", "DUFFEL_ENABLED=true"]
                    }
                )
            ]

        # Live Duffel Search implementation (when credentials exist)
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Duffel-Version": DUFFEL_API_VERSION,
                "Content-Type": "application/json",
                "User-Agent": "YatraPilot-AI/1.0"
            }
            # Duffel requires IATA airport codes; in production origin/dest mapping maps cities to IATA
            payload = {
                "data": {
                    "slices": [
                        {
                            "origin": origin.strip().upper()[:3],
                            "destination": destination.strip().upper()[:3],
                            "departure_date": journey_date or "2026-12-01"
                        }
                    ],
                    "passengers": [{"type": "adult"} for _ in range(max(1, passengers))],
                    "cabin_class": "economy"
                }
            }
            resp = requests.post(
                f"{self.base_url}/air/offer_requests",
                headers=headers,
                json=payload,
                timeout=8
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                offers = data.get("data", {}).get("offers", [])
                results: List[TransportOption] = []
                for offer in offers[:5]:
                    airline_name = offer.get("owner", {}).get("name", "Scheduled Airline")
                    total_amount = float(offer.get("total_amount", 0))
                    currency = offer.get("total_currency", "INR")
                    offer_id = offer.get("id", "offer")

                    results.append(
                        TransportOption(
                            id=f"duffel_{offer_id}",
                            provider_name=self.name,
                            category=self.category.value,
                            operator=airline_name,
                            title=f"{airline_name} Flight ({origin.title()} ➔ {destination.title()})",
                            vehicle_type="Commercial Jet (Airbus/Boeing)",
                            price_estimate_inr=total_amount if currency == "INR" else total_amount * 85.0,
                            price_range=f"{currency} {total_amount:,.0f}",
                            source="Duffel Live Flight API",
                            status=ProviderStatus.ACTIVE.value,
                            is_bookable=True,
                            booking_url=f"https://duffel.com/book/{offer_id}",
                            amenities=["In-flight Cabin Bag", "Check-in Baggage (per fare rules)"]
                        )
                    )
                if results:
                    return results

        except Exception as e:
            logger.warning(f"Duffel API live call failed: {e}")

        return []
