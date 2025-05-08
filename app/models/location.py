"""Location entity for the CabCab application."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Location:
    """
    Represents a location in the ride-hailing system.
    
    Attributes:
        id: Unique identifier for the location
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        address: Street address
        city: City name
        state: State or province
        postal_code: Postal or zip code
        country: Country name
        name: Optional name for the location (e.g., "Home", "Work")
        user_id: ID of the user if it's a saved location
    """
    latitude: float
    longitude: float
    address: str
    city: str
    state: str
    postal_code: str
    country: str
    id: UUID = None
    name: Optional[str] = None
    user_id: Optional[UUID] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.id is None:
            self.id = uuid4()
            
    @property
    def coordinates(self) -> tuple:
        """Get the coordinates as a tuple."""
        return (self.latitude, self.longitude)
    
    @property
    def full_address(self) -> str:
        """Get the full formatted address."""
        return f"{self.address}, {self.city}, {self.state} {self.postal_code}, {self.country}"