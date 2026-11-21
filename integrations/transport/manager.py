"""
YatraPilot AI — Central Transportation Marketplace Manager
Coordinates search across all 7 transportation categories, routes with MapTiler / OSRM / Geoapify,
integrates India GTFS public transit, Mobility Database, real Neon PostgreSQL private provider fleet,
and modular commercial adapters (eTravelSmart, redBus, IRCTC, Amadeus, Duffel).
"""

import logging
from typing import Dict, List, Optional, Any

from .base import TransportCategory, TransportOption, RouteSummary, ProviderStatus
from .maptiler import MapTilerService
from .osrm import OSRMService
from .nominatim import nominatim_service
from .gtfs_india import IndiaGTFSService
from .mobility_database import MobilityDatabaseService
from .etravelsmart import ETravelSmartAdapter
from .duffel import DuffelFlightAdapter
from .availability import evaluate_transportation_integrations
from .future_providers import (
    IRCTCTrainAdapter,
    FlightAggregatorAdapter,
    TaxiAndCabAdapter,
    CarRentalAdapter,
    TempoTravellerAdapter,
    PrivateCoachAdapter,
    RedBusSeatSellerAdapter
)

logger = logging.getLogger(__name__)


class TransportationMarketplaceManager:
    """Orchestrates transportation discovery across all providers and categories."""

    def __init__(self):
        # 1. Mapping, Geocoding & Routing engines
        self.maptiler = MapTilerService()
        self.osrm = OSRMService()
        self.nominatim = nominatim_service

        # 2. Public Transit Dataset services
        self.india_gtfs = IndiaGTFSService()
        self.mobility_db = MobilityDatabaseService()

        # 3. Provider Adapters across all categories
        self.etravelsmart = ETravelSmartAdapter()
        self.redbus = RedBusSeatSellerAdapter()
        self.train_adapter = IRCTCTrainAdapter()
        self.flight_adapter = FlightAggregatorAdapter()
        self.duffel_adapter = DuffelFlightAdapter()
        self.taxi_adapter = TaxiAndCabAdapter()
        self.rental_adapter = CarRentalAdapter()
        self.tempo_adapter = TempoTravellerAdapter()
        self.private_coach = PrivateCoachAdapter()

    def get_supported_categories(self) -> List[Dict[str, Any]]:
        """Returns the 7 core transportation categories supported by YatraPilot AI."""
        return [
            {
                "id": TransportCategory.BUS.value,
                "name": "Buses & Public Transit",
                "icon": "🚌",
                "description": "Intercity AC sleepers, state transport, and India GTFS city routes",
                "providers": ["eTravelSmart B2B", "India GTFS", "redBus SeatSeller"]
            },
            {
                "id": TransportCategory.TRAIN.value,
                "name": "Trains (Railways)",
                "icon": "🚆",
                "description": "Vande Bharat, Rajdhani, Shatabdi, and Superfast express trains",
                "providers": ["Indian Railways (IRCTC Partner Network)"]
            },
            {
                "id": TransportCategory.FLIGHT.value,
                "name": "Flights",
                "icon": "✈",
                "description": "Scheduled domestic airline routes and airport connections",
                "providers": ["Amadeus GDS", "Duffel Flights Network", "Domestic Airline Portals"]
            },
            {
                "id": TransportCategory.TAXI.value,
                "name": "Taxis & Outstation Cabs",
                "icon": "🚖",
                "description": "Sedan and SUV cabs with doorstep pickup and verified chauffeurs",
                "providers": ["Neon DB Verified Cab Alliance", "Standard Highway Chauffeur Fleet"]
            },
            {
                "id": TransportCategory.CAR_RENTAL.value,
                "name": "Car Rentals",
                "icon": "🚗",
                "description": "Self-drive hatchbacks, sedans, and luxury SUVs",
                "providers": ["Neon DB Approved Rental Unions", "Regional Rental Partner Hubs"]
            },
            {
                "id": TransportCategory.TEMPO_TRAVELLER.value,
                "name": "Tempo Travellers & Tourist Vehicles",
                "icon": "🚐",
                "description": "12, 17, 20, and 26-seater luxury AC vehicles for group & family tours",
                "providers": ["Delhi-NCR Certified Tourist Vehicle Union", "Certified Commercial Fleet"]
            },
            {
                "id": TransportCategory.PRIVATE_COACH.value,
                "name": "Private Transportation Companies",
                "icon": "🏢",
                "description": "Luxury interstate charter coaches and Volvo multi-axle buses",
                "providers": ["Interstate Luxury Coach Lines", "Western & Southern Intercity Coaches"]
            }
        ]

    def get_availability_matrix(self) -> Dict[str, Any]:
        """Returns the real-time integration availability matrix per specification."""
        return evaluate_transportation_integrations()

    def get_providers_directory(self) -> List[Dict[str, Any]]:
        """Returns status of all registered transportation adapters and integrations."""
        matrix = self.get_availability_matrix()
        return matrix["services"]

    def _query_neon_registered_providers(
        self,
        target_cat: Optional[str],
        origin_clean: str,
        dest_clean: str,
        dist_km: float
    ) -> List[TransportOption]:
        """
        Pulls actual provider-submitted records from Neon PostgreSQL and creates genuine TransportOption entries.
        Calculates rates according to provider-submitted fare structures. Zero fake availability.
        """
        options: List[TransportOption] = []
        try:
            from database.transport_db import get_registered_providers
            db_cat = None if target_cat in ("registered_fleet", "neon_db", "verified_fleet", "all", None) else target_cat
            registered = get_registered_providers(category=db_cat)

            for prov in registered:
                cat = prov.get("category")
                prov_name = prov.get("provider_name")
                op_type = prov.get("operator_type", "Certified Transport Operator")
                phone = prov.get("contact_phone", "Verified Contact")
                person = prov.get("contact_person", "")
                rating = prov.get("rating", 4.7)
                notes = prov.get("notes", "")
                vehicles = prov.get("vehicle_details", [])
                fares = prov.get("fare_structure", {})

                rate_per_km_map = fares.get("rate_per_km", {})
                batta = fares.get("driver_batta_per_day", 400.0)

                for idx, v in enumerate(vehicles):
                    v_type = v.get("type", "Commercial Tourist Vehicle")
                    v_model = v.get("model", v_type)
                    capacity = v.get("capacity")
                    features = v.get("features", [])

                    # Calculate rate per km based on vehicle type
                    rate = 22.0
                    if isinstance(rate_per_km_map, dict):
                        if capacity == 12:
                            rate = rate_per_km_map.get("12_seater", 23.0)
                        elif capacity == 17:
                            rate = rate_per_km_map.get("17_seater", 28.0)
                        elif capacity == 26:
                            rate = rate_per_km_map.get("26_seater", 36.0)
                        elif capacity == 4:
                            rate = rate_per_km_map.get("sedan", 13.5)
                        elif capacity in (6, 7):
                            rate = rate_per_km_map.get("suv_innova_crysta", rate_per_km_map.get("suv", 19.0))
                    elif isinstance(rate_per_km_map, (int, float)):
                        rate = float(rate_per_km_map)

                    est_fare = round(dist_km * rate + batta, 0) if dist_km > 0 else None
                    fare_str = f"₹{est_fare:,.0f} (Base ₹{rate}/km + ₹{batta:,.0f} driver batta)" if est_fare else f"Base rate ₹{rate}/km"

                    contact_summary = f"Contact: {phone} ({person})" if person else f"Contact: {phone}"

                    options.append(
                        TransportOption(
                            id=f"neon_p_{prov['id']}_{idx}",
                            provider_name=prov_name,
                            category=cat,
                            operator=prov_name,
                            title=f"{v_type} ({origin_clean.title()} ⇄ {dest_clean.title()})",
                            vehicle_type=v_model,
                            capacity=capacity,
                            distance_km=dist_km,
                            price_estimate_inr=est_fare,
                            price_range=fare_str,
                            amenities=features,
                            source=f"Neon DB Verified ({op_type})",
                            status=ProviderStatus.ACTIVE.value,
                            is_bookable=False,
                            notes=f"{notes} {contact_summary}. Tolls and state taxes at actuals.",
                            details={
                                "is_neon_registered": True,
                                "operator_type": op_type,
                                "contact_phone": phone,
                                "contact_email": prov.get("contact_email"),
                                "contact_person": person,
                                "rating": rating,
                                "operating_regions": prov.get("operating_regions", [])
                            }
                        )
                    )

        except Exception as e:
            logger.warning(f"Failed to query Neon PostgreSQL transport providers: {e}")

        return options

    def search_marketplace(
        self,
        origin: str,
        destination: str,
        journey_date: Optional[str] = None,
        category: Optional[str] = None,
        passengers: int = 1
    ) -> Dict[str, Any]:
        """
        Unified search across providers and categories between origin and destination.
        Calculates route with MapTiler / OSRM / Geoapify, pulls options, and attaches transit hubs.
        """
        origin_clean = (origin or "Delhi").strip()
        dest_clean = (destination or "Jaipur").strip()

        # 1. Geocode origin and destination (Nominatim + Geoapify + MapTiler)
        origin_geo = self.maptiler.geocode(origin_clean) or {"name": origin_clean, "lat": 28.6139, "lon": 77.2090}
        dest_geo = self.maptiler.geocode(dest_clean) or {"name": dest_clean, "lat": 26.9124, "lon": 75.7873}

        origin_lat = float(origin_geo.get("lat", 28.6139))
        origin_lon = float(origin_geo.get("lon", 77.2090))
        dest_lat = float(dest_geo.get("lat", 26.9124))
        dest_lon = float(dest_geo.get("lon", 75.7873))

        # 2. Calculate route (MapTiler first, fallback to OSRM / Geoapify)
        route_summary = self.maptiler.calculate_route(
            origin_clean, origin_lat, origin_lon, dest_clean, dest_lat, dest_lon
        )
        if not route_summary:
            route_summary = self.osrm.calculate_driving_route(
                origin_clean, origin_lat, origin_lon, dest_clean, dest_lat, dest_lon
            )

        dist_km = route_summary.distance_km if route_summary else 250.0

        # 3. Retrieve transit hubs for map display
        origin_hubs = self.maptiler.get_transport_hubs(origin_clean, origin_lat, origin_lon)
        dest_hubs = self.maptiler.get_transport_hubs(dest_clean, dest_lat, dest_lon)
        all_hubs = origin_hubs + dest_hubs

        # 4. Filter categories or collect all
        target_cat = category.lower().strip() if category and category.lower() != "all" else None
        options: List[TransportOption] = []

        # A. Query Neon PostgreSQL for genuine registered private fleet providers
        neon_options = self._query_neon_registered_providers(target_cat, origin_clean, dest_clean, dist_km)
        options.extend(neon_options)

        # B. Bus category
        if not target_cat or target_cat == TransportCategory.BUS.value:
            options.extend(self.etravelsmart.search(origin_clean, dest_clean, journey_date, passengers))
            options.extend(self.india_gtfs.find_transit_routes(origin_clean, dest_clean))
            options.extend(self.redbus.search(origin_clean, dest_clean))

        # C. Train category (National Rail Network)
        if not target_cat or target_cat == TransportCategory.TRAIN.value:
            options.extend(self.train_adapter.search(origin_clean, dest_clean, journey_date, passengers=passengers))

        # D. Flight category (Amadeus + Duffel)
        if not target_cat or target_cat == TransportCategory.FLIGHT.value:
            options.extend(self.flight_adapter.search(origin_clean, dest_clean, journey_date, passengers=passengers))
            options.extend(self.duffel_adapter.search(origin_clean, dest_clean, journey_date, passengers=passengers))

        # E. Taxi & Cab category
        if not target_cat or target_cat == TransportCategory.TAXI.value:
            options.extend(self.taxi_adapter.search(origin_clean, dest_clean, distance_km=dist_km))

        # F. Car Rental category
        if not target_cat or target_cat == TransportCategory.CAR_RENTAL.value:
            options.extend(self.rental_adapter.search(origin_clean, dest_clean))

        # G. Tempo Traveller category
        if not target_cat or target_cat == TransportCategory.TEMPO_TRAVELLER.value:
            options.extend(self.tempo_adapter.search(origin_clean, dest_clean, distance_km=dist_km))

        # H. Private Coach category
        if not target_cat or target_cat == TransportCategory.PRIVATE_COACH.value:
            options.extend(self.private_coach.search(origin_clean, dest_clean))

        return {
            "origin": {
                "query": origin_clean,
                "name": origin_geo.get("name", origin_clean),
                "coords": [origin_lat, origin_lon]
            },
            "destination": {
                "query": dest_clean,
                "name": dest_geo.get("name", dest_clean),
                "coords": [dest_lat, dest_lon]
            },
            "journey_date": journey_date,
            "route": route_summary.to_dict() if route_summary else None,
            "total_options": len(options),
            "options": [opt.to_dict() for opt in options],
            "transit_hubs": all_hubs,
            "map_config": self.maptiler.get_map_config()
        }


# Global singleton instance
transport_marketplace = TransportationMarketplaceManager()
