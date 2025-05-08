"""Ride entity for the CabCab application."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional
from uuid import UUID, uuid4


class RideStatus(Enum):
    """Possible statuses for a ride."""
    REQUESTED = auto()
    DRIVER_ASSIGNED = auto()
    DRIVER_EN_ROUTE = auto()
    DRIVER_ARRIVED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    CANCELLED = auto()


@dataclass
class Ride:
    """
    Represents a ride in the ride-hailing system.
    
    Attributes:
        id: Unique identifier for the ride
        user_id: ID of the user requesting the ride
        driver_id: ID of the assigned driver
        pickup_location_id: ID of the pickup location
        dropoff_location_id: ID of the dropoff location
        request_time: When the ride was requested
        start_time: When the ride started
        end_time: When the ride ended
        status: Current status of the ride
        estimated_fare: Estimated fare for the ride
        actual_fare: Final fare for the ride
        distance: Distance of the ride in kilometers
        duration: Duration of the ride in minutes
        payment_id: ID of the payment for this ride
        rating: Rating given by the user (1-5)
        feedback: Optional feedback from the user
    """
    user_id: UUID
    pickup_location_id: UUID
    dropoff_location_id: UUID
    estimated_fare: float
    distance: float
    duration: int
    id: UUID = None
    request_time: datetime = None
    driver_id: Optional[UUID] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: RideStatus = RideStatus.REQUESTED
    actual_fare: Optional[float] = None
    payment_id: Optional[UUID] = None
    rating: Optional[float] = None
    feedback: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.id is None:
            self.id = uuid4()
        if self.request_time is None:
            self.request_time = datetime.now()
            
    def assign_driver(self, driver_id: UUID) -> None:
        """Assign a driver to the ride."""
        self.driver_id = driver_id
        self.status = RideStatus.DRIVER_ASSIGNED
        
    def start_ride(self) -> None:
        """Start the ride."""
        self.start_time = datetime.now()
        self.status = RideStatus.IN_PROGRESS
        
    def complete_ride(self, actual_fare: float) -> None:
        """Complete the ride."""
        self.end_time = datetime.now()
        self.status = RideStatus.COMPLETED
        self.actual_fare = actual_fare
        
    def cancel_ride(self) -> None:
        """Cancel the ride."""
        self.status = RideStatus.CANCELLED