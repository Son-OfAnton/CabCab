"""Payment service for CabCab application."""

import os
import json
import requests
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.models.payment import PaymentMethod, PaymentStatus, Payment
from app.services.auth_service import AuthService, AuthError, UserType

# Base URL for our custom JSON server
BASE_URL = "http://localhost:3000"


class PaymentServiceError(Exception):
    """Custom exception for payment service errors."""
    pass


class MockCreditCardProcessor:
    """Mock implementation of a credit card processor."""
    
    @staticmethod
    def validate_card(card_number: str, expiry_month: int, expiry_year: int, cvv: str) -> bool:
        """
        Validate a credit card.
        
        Args:
            card_number: Card number
            expiry_month: Expiry month (1-12)
            expiry_year: Expiry year (4 digits)
            cvv: CVV code
            
        Returns:
            bool: True if card is valid, False otherwise
        """
        # Check card number length (simplified validation)
        if not (13 <= len(card_number.replace(" ", "")) <= 19):
            return False
            
        # Check if card number contains only digits
        if not card_number.replace(" ", "").isdigit():
            return False
            
        # Check expiration date
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        if expiry_year < current_year:
            return False
        if expiry_year == current_year and expiry_month < current_month:
            return False
            
        # Check expiry_month range
        if not 1 <= expiry_month <= 12:
            return False
            
        # Check CVV (simplified)
        if not (len(cvv) in [3, 4] and cvv.isdigit()):
            return False
            
        return True
    
    @staticmethod
    def tokenize_card(card_number: str, expiry_month: int, expiry_year: int, cardholder_name: str) -> Dict[str, Any]:
        """
        Create a payment token for a credit card.
        
        Args:
            card_number: Card number
            expiry_month: Expiry month (1-12)
            expiry_year: Expiry year (4 digits)
            cardholder_name: Name on the card
            
        Returns:
            Dict: Payment token information
        """
        # Mask the card number for display
        masked_number = "xxxx-xxxx-xxxx-" + card_number.replace(" ", "")[-4:]
        
        # Create a simulated token
        token = {
            "token_id": str(uuid.uuid4()),
            "card_type": _detect_card_type(card_number),
            "last_four": card_number.replace(" ", "")[-4:],
            "expiry_month": expiry_month,
            "expiry_year": expiry_year,
            "cardholder_name": cardholder_name,
            "masked_number": masked_number,
            "created_at": datetime.now().isoformat()
        }
        
        return token
        

class MockPaypalProcessor:
    """Mock implementation of a PayPal processor."""
    
    @staticmethod
    def validate_account(email: str) -> bool:
        """
        Validate a PayPal account.
        
        Args:
            email: PayPal account email
            
        Returns:
            bool: True if account is valid, False otherwise
        """
        # Simple email validation
        return "@" in email and "." in email.split("@")[1]
    
    @staticmethod
    def tokenize_account(email: str) -> Dict[str, Any]:
        """
        Create a payment token for a PayPal account.
        
        Args:
            email: PayPal account email
            
        Returns:
            Dict: Payment token information
        """
        # Create a simulated token
        token = {
            "token_id": str(uuid.uuid4()),
            "email": email,
            "account_type": "PAYPAL",
            "created_at": datetime.now().isoformat()
        }
        
        return token


class PaymentService:
    """Service for handling payment operations."""
    
    @staticmethod
    def add_payment_method(token: str, payment_type: str, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a payment method to a user's account.
        
        Args:
            token: JWT token for authentication
            payment_type: Type of payment method (CREDIT_CARD, PAYPAL, etc.)
            payment_details: Details required for the specific payment method
            
        Returns:
            Dict: The saved payment method
            
        Raises:
            PaymentServiceError: If adding the payment method fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a passenger
            user = AuthService.require_user_type(token, [UserType.PASSENGER.value])
            
            # Initialize payment data
            payment_data = {
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "payment_type": payment_type,
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Process based on payment type
            if payment_type == "CREDIT_CARD":
                # Validate credit card details
                card_processor = MockCreditCardProcessor()
                
                card_number = payment_details.get("card_number", "")
                expiry_month = int(payment_details.get("expiry_month", 0))
                expiry_year = int(payment_details.get("expiry_year", 0))
                cvv = payment_details.get("cvv", "")
                cardholder_name = payment_details.get("cardholder_name", "")
                
                if not card_processor.validate_card(card_number, expiry_month, expiry_year, cvv):
                    raise PaymentServiceError("Invalid credit card details")
                
                # Tokenize the card (in a real implementation, this would securely store card details)
                card_token = card_processor.tokenize_card(
                    card_number, expiry_month, expiry_year, cardholder_name
                )
                
                payment_data["token"] = card_token
                payment_data["card_type"] = card_token["card_type"]
                payment_data["last_four"] = card_token["last_four"]
                payment_data["expiry"] = f"{expiry_month:02d}/{expiry_year}"
                payment_data["display_name"] = f"{card_token['card_type']} ending in {card_token['last_four']}"
                
            elif payment_type == "PAYPAL":
                # Validate PayPal account
                paypal_processor = MockPaypalProcessor()
                
                paypal_email = payment_details.get("email", "")
                
                if not paypal_processor.validate_account(paypal_email):
                    raise PaymentServiceError("Invalid PayPal account")
                
                # Tokenize the PayPal account
                paypal_token = paypal_processor.tokenize_account(paypal_email)
                
                payment_data["token"] = paypal_token
                payment_data["email"] = paypal_email
                payment_data["display_name"] = f"PayPal ({paypal_email})"
                
            else:
                raise PaymentServiceError(f"Unsupported payment type: {payment_type}")
            
            # Save the payment method to the database
            response = requests.post(f"{BASE_URL}/payment_methods", json=payment_data)
            response.raise_for_status()
            saved_payment_method = response.json()
            
            # Check if this is the user's first payment method
            response = requests.get(f"{BASE_URL}/payment_methods/query?user_id={user['id']}")
            
            if response.status_code == 200:
                user_payment_methods = response.json()
                
                if len(user_payment_methods) == 1:
                    # This is the first payment method, set it as default
                    saved_payment_method["is_default"] = True
                    
                    # Update the payment method
                    response = requests.put(
                        f"{BASE_URL}/payment_methods/{saved_payment_method['id']}", 
                        json=saved_payment_method
                    )
                    response.raise_for_status()
                    saved_payment_method = response.json()
            
            # Add the payment method to the user's payment_methods array
            if not user.get("payment_methods"):
                user["payment_methods"] = []
            
            user["payment_methods"].append(saved_payment_method["id"])
            user["updated_at"] = datetime.now().isoformat()
            
            # Update user in database
            response = requests.put(f"{BASE_URL}/users/{user['id']}", json=user)
            response.raise_for_status()
            
            return saved_payment_method
            
        except requests.RequestException as e:
            raise PaymentServiceError(f"Failed to add payment method: {str(e)}")

    @staticmethod
    def get_payment_methods(token: str) -> List[Dict[str, Any]]:
        """
        Get all payment methods for a user.
        
        Args:
            token: JWT token for authentication
            
        Returns:
            List[Dict]: List of payment methods
            
        Raises:
            PaymentServiceError: If retrieving payment methods fails
            AuthError: If authentication fails
        """
        try:
            # Verify token
            user = AuthService.verify_token(token)
            
            # Get all payment methods for this user
            response = requests.get(f"{BASE_URL}/payment_methods/query?user_id={user['id']}")
            
            if response.status_code == 404:
                return []  # No payment methods found
                
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise PaymentServiceError(f"Failed to retrieve payment methods: {str(e)}")

    @staticmethod
    def set_default_payment_method(token: str, payment_method_id: str) -> Dict[str, Any]:
        """
        Set a payment method as the default.
        
        Args:
            token: JWT token for authentication
            payment_method_id: ID of the payment method to set as default
            
        Returns:
            Dict: The updated payment method
            
        Raises:
            PaymentServiceError: If setting default payment method fails
            AuthError: If authentication fails
        """
        try:
            # Verify token
            user = AuthService.verify_token(token)
            
            # Get the payment method
            response = requests.get(f"{BASE_URL}/payment_methods/{payment_method_id}")
            
            if response.status_code == 404:
                raise PaymentServiceError(f"Payment method with ID {payment_method_id} not found")
                
            response.raise_for_status()
            payment_method = response.json()
            
            # Check if payment method belongs to this user
            if payment_method.get("user_id") != user["id"]:
                raise PaymentServiceError("You do not have permission to modify this payment method")
            
            # Get all payment methods for this user
            response = requests.get(f"{BASE_URL}/payment_methods/query?user_id={user['id']}")
            
            if response.status_code != 404:  # Only process if payment methods exist
                response.raise_for_status()
                user_payment_methods = response.json()
                
                # Unset default for all payment methods
                for method in user_payment_methods:
                    if method.get("is_default") and method["id"] != payment_method_id:
                        method["is_default"] = False
                        update_response = requests.put(
                            f"{BASE_URL}/payment_methods/{method['id']}",
                            json=method
                        )
                        update_response.raise_for_status()
            
            # Set this payment method as default
            payment_method["is_default"] = True
            payment_method["updated_at"] = datetime.now().isoformat()
            
            # Update the payment method
            response = requests.put(
                f"{BASE_URL}/payment_methods/{payment_method_id}",
                json=payment_method
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            raise PaymentServiceError(f"Failed to set default payment method: {str(e)}")

    @staticmethod
    def remove_payment_method(token: str, payment_method_id: str) -> bool:
        """
        Remove a payment method from a user's account.
        
        Args:
            token: JWT token for authentication
            payment_method_id: ID of the payment method to remove
            
        Returns:
            bool: True if removal was successful
            
        Raises:
            PaymentServiceError: If removing the payment method fails
            AuthError: If authentication fails
        """
        try:
            # Verify token
            user = AuthService.verify_token(token)
            
            # Get the payment method
            response = requests.get(f"{BASE_URL}/payment_methods/{payment_method_id}")
            
            if response.status_code == 404:
                raise PaymentServiceError(f"Payment method with ID {payment_method_id} not found")
                
            response.raise_for_status()
            payment_method = response.json()
            
            # Check if payment method belongs to this user
            if payment_method.get("user_id") != user["id"]:
                raise PaymentServiceError("You do not have permission to remove this payment method")
            
            # Remove payment method ID from user's payment methods array
            if user.get("payment_methods") and payment_method_id in user["payment_methods"]:
                user["payment_methods"].remove(payment_method_id)
                user["updated_at"] = datetime.now().isoformat()
                
                # Update user in database
                user_update_response = requests.put(f"{BASE_URL}/users/{user['id']}", json=user)
                user_update_response.raise_for_status()
            
            # Check if this is the default payment method
            was_default = payment_method.get("is_default", False)
            
            # Delete the payment method
            response = requests.delete(f"{BASE_URL}/payment_methods/{payment_method_id}")
            response.raise_for_status()
            
            # If removed method was default, set a new default if one exists
            if was_default:
                response = requests.get(f"{BASE_URL}/payment_methods/query?user_id={user['id']}")
                
                if response.status_code == 200:
                    remaining_methods = response.json()
                    
                    if remaining_methods:
                        # Set the first remaining payment method as default
                        new_default = remaining_methods[0]
                        new_default["is_default"] = True
                        new_default["updated_at"] = datetime.now().isoformat()
                        
                        # Update the payment method
                        update_response = requests.put(
                            f"{BASE_URL}/payment_methods/{new_default['id']}",
                            json=new_default
                        )
                        update_response.raise_for_status()
            
            return True
            
        except requests.RequestException as e:
            raise PaymentServiceError(f"Failed to remove payment method: {str(e)}")


def _detect_card_type(card_number: str) -> str:
    """
    Detect credit card type based on the card number.
    
    Args:
        card_number: Credit card number
        
    Returns:
        str: Card type (VISA, MASTERCARD, AMEX, etc.)
    """
    # Remove spaces and dashes
    number = card_number.replace(" ", "").replace("-", "")
    
    # Check for VISA
    if number.startswith('4'):
        return "VISA"
    
    # Check for Mastercard
    if number.startswith('5') and 1 <= int(number[1]) <= 5:
        return "MASTERCARD"
    
    # Check for American Express
    if number.startswith(('34', '37')):
        return "AMEX"
    
    # Check for Discover
    if number.startswith('6'):
        return "DISCOVER"
    
    # Default
    return "UNKNOWN"