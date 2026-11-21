"""
YatraPilot AI — Transportation Marketplace Base Architecture
Defines data models, categories, provider statuses, and base provider classes.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any


class TransportCategory(str, Enum):
    BUS = "bus"
    TRAIN = "train"
    FLIGHT = "flight"
    TAXI = "taxi"
    CAR_RENTAL = "car_rental"
    TEMPO_TRAVELLER = "tempo_traveller"
    PRIVATE_COACH = "private_coach"


class ProviderStatus(str, Enum):
    ACTIVE = "active"
    FEED_ACTIVE = "feed_active"
    AWAITING_CREDENTIALS = "awaiting_partner_credentials"
    MAINTENANCE = "maintenance"


@dataclass
class TransportOption:
    """Standardized representation of any transportation option in the marketplace."""
    id: str
    provider_name: str
    category: str  # TransportCategory value
    operator: str
    title: str
    vehicle_type: str
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    duration_str: Optional[str] = None
    duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    price_estimate_inr: Optional[float] = None
    price_range: Optional[str] = None
    seats_available: Optional[int] = None
    capacity: Optional[int] = None
    amenities: List[str] = field(default_factory=list)
    boarding_points: List[str] = field(default_factory=list)
    dropping_points: List[str] = field(default_factory=list)
    source: str = "YatraPilot Provider Registry"
    status: str = ProviderStatus.ACTIVE.value
    notes: Optional[str] = None
    booking_url: Optional[str] = None
    is_bookable: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RouteSummary:
    """Standardized road/transit route calculated by MapTiler or OSRM."""
    origin_name: str
    origin_coords: List[float]  # [lat, lon]
    destination_name: str
    destination_coords: List[float]  # [lat, lon]
    distance_km: float
    duration_minutes: int
    duration_str: str
    routing_engine: str  # "maptiler" | "osrm" | "direct"
    geometry_geojson: Optional[Dict[str, Any]] = None  # GeoJSON LineString
    waypoints: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseTransportProvider:
    """Abstract interface for all transportation discovery adapters."""

    name: str = "BaseProvider"
    category: TransportCategory = TransportCategory.BUS

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url

    def get_status(self) -> Dict[str, Any]:
        """Returns provider integration health, credential state, and capabilities."""
        return {
            "name": self.name,
            "category": self.category.value,
            "is_configured": bool(self.api_key),
            "status": ProviderStatus.ACTIVE.value if self.api_key else ProviderStatus.AWAITING_CREDENTIALS.value
        }

    def search(
        self,
        origin: str,
        destination: str,
        journey_date: Optional[str] = None,
        passengers: int = 1,
        **kwargs
    ) -> List[TransportOption]:
        """Search for transportation options between origin and destination."""
        raise NotImplementedError("Subclasses must implement search()")
