from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional, List
from uuid import UUID, uuid4


class UserType(Enum):
    """Types of users in the system."""
    PASSENGER = auto()
    DRIVER = auto()
    ADMIN = auto()


@dataclass
class User:
    """
    Represents a user in the ride-hailing system.
    
    Attributes:
        id: Unique identifier for the user
        email: User's email address
        password: Hashed password
        first_name: User's first name
        last_name: User's last name
        phone: User's phone number
        user_type: Type of user (passenger, driver, or admin)
        created_at: When the user account was created
        updated_at: When the user account was last updated
        rating: User's average rating (1-5)
        is_active: Whether the user account is active
        payment_methods: List of saved payment method IDs (for passengers)
        license_number: Driver's license number (for drivers)
        is_verified: Whether the driver is verified (for drivers)
        is_available: Whether the driver is available for rides (for drivers)
        vehicle_id: ID of the driver's vehicle (for drivers)
    """
    email: str
    password: str
    first_name: str
    last_name: str
    phone: str
    user_type: UserType
    id: str = None
    created_at: str = None
    updated_at: str = None
    rating: Optional[float] = None
    is_active: bool = True
    
    # Passenger specific attributes
    payment_methods: List[str] = None
    
    # Driver specific attributes
    license_number: Optional[str] = None
    is_verified: bool = False
    is_available: bool = False
    vehicle_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.id is None:
            self.id = str(uuid4())
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.payment_methods is None:
            self.payment_methods = []
    
    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_passenger(self) -> bool:
        """Check if user is a passenger."""
        return self.user_type == UserType.PASSENGER
    
    @property
    def is_driver(self) -> bool:
        """Check if user is a driver."""
        return self.user_type == UserType.DRIVER
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.user_type == UserType.ADMIN