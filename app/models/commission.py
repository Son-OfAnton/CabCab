"""
Commission model for the CabCab application.

This module defines the CommissionSetting class which is used to store
the commission settings for the ride-hailing platform.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class CommissionSetting:
    """
    Stores the commission settings for the platform.
    
    Attributes:
        id: Unique identifier for the commission setting
        admin_id: ID of the admin who receives the commission
        payment_method_id: ID of the payment method to receive commission
        percentage: Commission percentage (default: 10%)
        is_active: Whether commission collection is active
        created_at: When the setting was created
        updated_at: When the setting was last updated
    """
    admin_id: str
    payment_method_id: str
    percentage: float = 10.0
    is_active: bool = True
    id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.id is None:
            self.id = str(uuid4())
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at

    @property
    def percentage_decimal(self) -> float:
        """Get the commission percentage as a decimal value for calculations."""
        return self.percentage / 100.0