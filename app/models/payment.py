"""Payment entity for the CabCab application."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Dict, Any
from uuid import UUID, uuid4


class PaymentMethod(Enum):
    """Types of payment methods available in the system."""
    CREDIT_CARD = "CREDIT_CARD"
    PAYPAL = "PAYPAL"
    APPLE_PAY = "APPLE_PAY"
    GOOGLE_PAY = "GOOGLE_PAY"
    CASH = "CASH"


class PaymentStatus(Enum):
    """Possible statuses for a payment."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


@dataclass
class Payment:
    """
    Represents a payment in the ride-hailing system.
    
    Attributes:
        id: Unique identifier for the payment
        ride_id: ID of the ride this payment is for
        user_id: ID of the user making the payment
        amount: Payment amount
        payment_method_id: ID of the payment method used
        status: Current status of the payment
        transaction_id: External payment processor transaction ID
        created_at: When the payment was created
        updated_at: When the payment was last updated
        is_refunded: Whether the payment has been refunded
    """
    ride_id: str
    user_id: str
    amount: float
    payment_method_id: str
    id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_refunded: bool = False
    
    def __post_init__(self):
        """Initialize default values."""
        if self.id is None:
            self.id = str(uuid4())
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at


@dataclass
class PaymentMethodToken:
    """
    Represents a tokenized payment method in the system.
    
    This is a secure representation of payment details that doesn't store 
    sensitive information directly.
    """
    id: str
    user_id: str
    payment_type: str  # CREDIT_CARD, PAYPAL, etc.
    token: Dict[str, Any]  # Tokenized payment information
    display_name: str  # User-friendly name for displaying the payment method
    is_default: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at