"""User entity for the CabCab application."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4


@dataclass
class User:
    """
    Represents a passenger/user in the ride-hailing system.
    
    Attributes:
        id: Unique identifier for the user
        first_name: User's first name
        last_name: User's last name
        email: User's email address
        phone: User's phone number
        created_at: When the user account was created
        rating: User's average rating (1-5)
        is_active: Whether the user account is active
        payment_methods: List of saved payment method IDs
    """
    first_name: str
    last_name: str
    email: str
    phone: str
    id: UUID = None
    created_at: datetime = None
    rating: Optional[float] = None
    is_active: bool = True
    payment_methods: List[UUID] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.id is None:
            self.id = uuid4()
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.payment_methods is None:
            self.payment_methods = []
            
    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        return f"{self.first_name} {self.last_name}"