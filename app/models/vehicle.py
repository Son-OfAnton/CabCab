"""Vehicle entity for the CabCab application."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional
from uuid import UUID, uuid4


class VehicleType(Enum):
    """Types of vehicles available in the system."""
    ECONOMY = auto()
    COMFORT = auto()
    PREMIUM = auto()
    SUV = auto()
    XL = auto()


@dataclass
class Vehicle:
    """
    Represents a vehicle in the ride-hailing system.
    
    Attributes:
        id: Unique identifier for the vehicle
        make: Vehicle manufacturer
        model: Vehicle model
        year: Vehicle year
        color: Vehicle color
        license_plate: Vehicle license plate
        vehicle_type: Type of vehicle
        capacity: Maximum number of passengers
        created_at: When the vehicle was added to the system
        driver_id: ID of the driver who owns this vehicle
        is_active: Whether the vehicle is active in the system
    """
    make: str
    model: str
    year: int
    color: str
    license_plate: str
    vehicle_type: VehicleType
    capacity: int
    id: UUID = None
    created_at: datetime = None
    driver_id: Optional[UUID] = None
    is_active: bool = True
    
    def __post_init__(self):
        """Initialize default values."""
        if self.id is None:
            self.id = uuid4()
        if self.created_at is None:
            self.created_at = datetime.now()