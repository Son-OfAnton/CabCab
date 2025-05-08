"""Driver entity for the CabCab application."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4


@dataclass
class Driver:
    """
    Represents a driver in the ride-hailing system.
    
    Attributes:
        id: Unique identifier for the driver
        first_name: Driver's first name
        last_name: Driver's last name
        email: Driver's email address
        phone: Driver's phone number
        license_number: Driver's license number
        created_at: When the driver account was created
        rating: Driver's average rating (1-5)
        is_active: Whether the driver account is active
        is_available: Whether the driver is currently available for rides
        vehicle_id: ID of the driver's vehicle
        current_location: Current location coordinates (lat, lng)
    """
    first_name: str
    last_name: str
    email: str
    phone: str
    license_number: str
    id: UUID = None
    created_at: datetime = None
    rating: Optional[float] = None
    is_active: bool = True
    is_available: bool = False
    vehicle_id: Optional[UUID] = None
    current_location: Optional[tuple] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.id is None:
            self.id = uuid4()
        if self.created_at is None:
            self.created_at = datetime.now()
            
    @property
    def full_name(self) -> str:
        """Get the driver's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def update_location(self, latitude: float, longitude: float) -> None:
        """Update the driver's current location."""
        self.current_location = (latitude, longitude)
        
    def update_availability(self, is_available: bool) -> None:
        """Update the driver's availability status."""
        self.is_available = is_available