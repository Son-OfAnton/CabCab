"""Payment entity for the CabCab application."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional
from uuid import UUID, uuid4


class PaymentMethod(Enum):
    """Types of payment methods available in the system."""
    CREDIT_CARD = auto()
    DEBIT_CARD = auto()
    PAYPAL = auto()
    APPLE_PAY = auto()
    GOOGLE_PAY = auto()
    CASH = auto()


class PaymentStatus(Enum):
    """Possible statuses for a payment."""
    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()
    REFUNDED = auto()


@dataclass
class Payment:
    """
    Represents a payment in the ride-hailing system.
    
    Attributes:
        id: Unique identifier for the payment
        ride_id: ID of the ride this payment is for
        user_id: ID of the user making the payment
        amount: Payment amount
        payment_method: Method of payment
        status: Current status of the payment
        transaction_id: External payment processor transaction ID
        created_at: When the payment was created
        updated_at: When the payment was last updated
        is_refunded: Whether the payment has been refunded
    """
    ride_id: UUID
    user_id: UUID
    amount: float
    payment_method: PaymentMethod
    id: UUID = None
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: Optional[str] = None
    created_at: datetime = None
    updated_at: Optional[datetime] = None
    is_refunded: bool = False
    
    def __post_init__(self):
        """Initialize default values."""
        if self.id is None:
            self.id = uuid4()
        if self.created_at is None:
            self.created_at = datetime.now()
            
    def update_status(self, status: PaymentStatus) -> None:
        """Update the payment status."""
        self.status = status
        self.updated_at = datetime.now()
        
    def process_payment(self, transaction_id: str) -> None:
        """Process the payment."""
        self.transaction_id = transaction_id
        self.status = PaymentStatus.COMPLETED
        self.updated_at = datetime.now()
        
    def refund_payment(self) -> None:
        """Refund the payment."""
        self.is_refunded = True
        self.status = PaymentStatus.REFUNDED
        self.updated_at = datetime.now()