"""Commission service for the CabCab application."""

import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.models.commission import CommissionSetting
from app.services.auth_service import AuthService, AuthError, UserType

# Base URL for our custom JSON server
BASE_URL = "http://localhost:3000"


class CommissionServiceError(Exception):
    """Custom exception for commission service errors."""
    pass


class CommissionService:
    """Service for handling commission operations."""
    
    COMMISSION_COLLECTION = "commissions"
    
    @staticmethod
    def set_admin_commission(token: str, payment_method_id: str, percentage: float = 10.0) -> Dict[str, Any]:
        """
        Set up or update commission settings.
        
        Args:
            token: JWT token for authentication (admin only)
            payment_method_id: ID of the payment method to receive commissions
            percentage: Commission percentage (default: 10%)
            
        Returns:
            Dict: The commission settings
        
        Raises:
            CommissionServiceError: If commission setup fails
            AuthError: If authentication fails or user is not an admin
        """
        try:
            # Verify token and ensure user is an admin
            admin = AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Validate percentage (between 0 and 50)
            if not 0 <= percentage <= 50:
                raise CommissionServiceError("Commission percentage must be between 0 and 50%")
            
            # Verify payment method exists and belongs to this admin
            response = requests.get(f"{BASE_URL}/payments/query?id={payment_method_id}&user_id={admin['id']}")
            if response.status_code != 200 or not response.json():
                raise CommissionServiceError("Payment method not found or does not belong to you")
            
            # Check if there's an existing commission setting
            response = requests.get(f"{BASE_URL}/{CommissionService.COMMISSION_COLLECTION}/query?admin_id={admin['id']}")
            existing_settings = response.json() if response.status_code == 200 else []
            
            if existing_settings:
                # Update existing settings
                commission_setting = existing_settings[0]
                commission_setting["payment_method_id"] = payment_method_id
                commission_setting["percentage"] = percentage
                commission_setting["updated_at"] = datetime.now().isoformat()
                
                response = requests.put(
                    f"{BASE_URL}/{CommissionService.COMMISSION_COLLECTION}/{commission_setting['id']}", 
                    json=commission_setting
                )
            else:
                # Create new settings
                commission_setting = CommissionSetting(
                    admin_id=admin["id"],
                    payment_method_id=payment_method_id,
                    percentage=percentage
                ).__dict__
                
                response = requests.post(
                    f"{BASE_URL}/{CommissionService.COMMISSION_COLLECTION}", 
                    json=commission_setting
                )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise CommissionServiceError(f"Failed to set commission settings: {str(e)}")
    
    @staticmethod
    def get_admin_commission(token: str) -> Dict[str, Any]:
        """
        Get commission settings and statistics.
        
        Args:
            token: JWT token for authentication (admin only)
            
        Returns:
            Dict: Commission settings and statistics
            
        Raises:
            CommissionServiceError: If retrieval fails
            AuthError: If authentication fails or user is not an admin
        """
        try:
            # Verify token and ensure user is an admin
            admin = AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Get commission settings
            response = requests.get(f"{BASE_URL}/{CommissionService.COMMISSION_COLLECTION}/query?admin_id={admin['id']}")
            
            if response.status_code != 200 or not response.json():
                return {
                    "settings": None,
                    "statistics": {
                        "total_earned": 0.0,
                        "ride_count": 0,
                        "recent_transactions": []
                    }
                }
            
            commission_setting = response.json()[0]
            
            # Get payment method details
            payment_method_response = requests.get(f"{BASE_URL}/payments/{commission_setting['payment_method_id']}")
            if payment_method_response.status_code == 200:
                commission_setting["payment_method"] = payment_method_response.json()
            
            # Get commission payments statistics
            payments_response = requests.get(f"{BASE_URL}/payments/query?admin_id={admin['id']}&is_commission=true")
            commission_payments = payments_response.json() if payments_response.status_code == 200 else []
            
            # Calculate statistics
            total_earned = sum(payment.get("amount", 0.0) for payment in commission_payments)
            ride_count = len(commission_payments)
            
            # Sort by date (newest first) and limit to 5 recent transactions
            recent_transactions = sorted(
                commission_payments, 
                key=lambda p: p.get("created_at", ""), 
                reverse=True
            )[:5]
            
            # Add ride details to transactions
            for transaction in recent_transactions:
                ride_id = transaction.get("ride_id")
                if ride_id:
                    ride_response = requests.get(f"{BASE_URL}/rides/{ride_id}")
                    if ride_response.status_code == 200:
                        transaction["ride"] = ride_response.json()
            
            return {
                "settings": commission_setting,
                "statistics": {
                    "total_earned": total_earned,
                    "ride_count": ride_count,
                    "recent_transactions": recent_transactions
                }
            }
            
        except requests.RequestException as e:
            raise CommissionServiceError(f"Failed to get commission settings: {str(e)}")
    
    @staticmethod
    def enable_admin_commission(token: str) -> Dict[str, Any]:
        """
        Enable commission collection.
        
        Args:
            token: JWT token for authentication (admin only)
            
        Returns:
            Dict: Updated commission settings
            
        Raises:
            CommissionServiceError: If enabling fails
            AuthError: If authentication fails or user is not an admin
        """
        try:
            # Verify token and ensure user is an admin
            admin = AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Get commission settings
            response = requests.get(f"{BASE_URL}/{CommissionService.COMMISSION_COLLECTION}/query?admin_id={admin['id']}")
            
            if response.status_code != 200 or not response.json():
                raise CommissionServiceError("Commission settings not found. Please set up commission details first.")
            
            commission_setting = response.json()[0]
            
            # Update active status
            commission_setting["is_active"] = True
            commission_setting["updated_at"] = datetime.now().isoformat()
            
            # Save updated settings
            response = requests.put(
                f"{BASE_URL}/{CommissionService.COMMISSION_COLLECTION}/{commission_setting['id']}", 
                json=commission_setting
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise CommissionServiceError(f"Failed to enable commission: {str(e)}")
    
    @staticmethod
    def disable_admin_commission(token: str) -> Dict[str, Any]:
        """
        Disable commission collection.
        
        Args:
            token: JWT token for authentication (admin only)
            
        Returns:
            Dict: Updated commission settings
            
        Raises:
            CommissionServiceError: If disabling fails
            AuthError: If authentication fails or user is not an admin
        """
        try:
            # Verify token and ensure user is an admin
            admin = AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Get commission settings
            response = requests.get(f"{BASE_URL}/{CommissionService.COMMISSION_COLLECTION}/query?admin_id={admin['id']}")
            
            if response.status_code != 200 or not response.json():
                raise CommissionServiceError("Commission settings not found. Please set up commission details first.")
            
            commission_setting = response.json()[0]
            
            # Update active status
            commission_setting["is_active"] = False
            commission_setting["updated_at"] = datetime.now().isoformat()
            
            # Save updated settings
            response = requests.put(
                f"{BASE_URL}/{CommissionService.COMMISSION_COLLECTION}/{commission_setting['id']}", 
                json=commission_setting
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise CommissionServiceError(f"Failed to disable commission: {str(e)}")