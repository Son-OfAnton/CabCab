"""Payment service for CabCab application."""

import os
import json
import requests
import uuid 
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.models.payment import PaymentMethod, PaymentStatus, Payment
from app.models.ride import RideStatus
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
            user = AuthService.require_user_type(
                token, [UserType.PASSENGER.value])

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
                raise PaymentServiceError(
                    f"Unsupported payment type: {payment_type}")

            # Save the payment method to the database
            response = requests.post(
                f"{BASE_URL}/payment_methods", json=payment_data)
            response.raise_for_status()
            saved_payment_method = response.json()

            # Check if this is the user's first payment method
            response = requests.get(
                f"{BASE_URL}/payment_methods/query?user_id={user['id']}")

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
            response = requests.put(
                f"{BASE_URL}/users/{user['id']}", json=user)
            response.raise_for_status()

            return saved_payment_method

        except requests.RequestException as e:
            raise PaymentServiceError(
                f"Failed to add payment method: {str(e)}")

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
            response = requests.get(
                f"{BASE_URL}/payment_methods/query?user_id={user['id']}")

            if response.status_code == 404:
                return []  # No payment methods found

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            raise PaymentServiceError(
                f"Failed to retrieve payment methods: {str(e)}")

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
            response = requests.get(
                f"{BASE_URL}/payment_methods/{payment_method_id}")

            if response.status_code == 404:
                raise PaymentServiceError(
                    f"Payment method with ID {payment_method_id} not found")

            response.raise_for_status()
            payment_method = response.json()

            # Check if payment method belongs to this user
            if payment_method.get("user_id") != user["id"]:
                raise PaymentServiceError(
                    "You do not have permission to modify this payment method")

            # Get all payment methods for this user
            response = requests.get(
                f"{BASE_URL}/payment_methods/query?user_id={user['id']}")

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
            raise PaymentServiceError(
                f"Failed to set default payment method: {str(e)}")

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
            response = requests.get(
                f"{BASE_URL}/payment_methods/{payment_method_id}")

            if response.status_code == 404:
                raise PaymentServiceError(
                    f"Payment method with ID {payment_method_id} not found")

            response.raise_for_status()
            payment_method = response.json()

            # Check if payment method belongs to this user
            if payment_method.get("user_id") != user["id"]:
                raise PaymentServiceError(
                    "You do not have permission to remove this payment method")

            # Remove payment method ID from user's payment methods array
            if user.get("payment_methods") and payment_method_id in user["payment_methods"]:
                user["payment_methods"].remove(payment_method_id)
                user["updated_at"] = datetime.now().isoformat()

                # Update user in database
                user_update_response = requests.put(
                    f"{BASE_URL}/users/{user['id']}", json=user)
                user_update_response.raise_for_status()

            # Check if this is the default payment method
            was_default = payment_method.get("is_default", False)

            # Delete the payment method
            response = requests.delete(
                f"{BASE_URL}/payment_methods/{payment_method_id}")
            response.raise_for_status()

            # If removed method was default, set a new default if one exists
            if was_default:
                response = requests.get(
                    f"{BASE_URL}/payment_methods/query?user_id={user['id']}")

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
            raise PaymentServiceError(
                f"Failed to remove payment method: {str(e)}")

    # Add these methods to the PaymentService class

    @staticmethod
    def add_driver_payment_method(token: str, payment_type: str, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new payment method for a driver to receive earnings.

        Args:
            token: JWT token for authentication (drivers only)
            payment_type: Type of payment method (BANK_ACCOUNT, PAYPAL)
            payment_details: Details for the payment method

        Returns:
            Dict: The added payment method

        Raises:
            PaymentServiceError: If payment method addition fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            user = AuthService.require_user_type(
                token, [UserType.DRIVER.value])

            # Sanitize payment details before processing
            sanitized_details = _sanitize_payment_details(
                payment_type, payment_details)

            # Validate payment details based on type
            if payment_type == "BANK_ACCOUNT":
                # Validate bank account details
                if not sanitized_details.get("account_number") or \
                        not sanitized_details.get("routing_number") or \
                        not sanitized_details.get("account_holder_name"):
                    raise PaymentServiceError(
                        "Incomplete bank account details")

                # Format account number for display (masked)
                account_number = sanitized_details["account_number"]
                masked_account = f"****{account_number[-4:]}" if len(
                    account_number) >= 4 else "****"

                if sanitized_details.get("bank_name"):
                    display_name = f"{sanitized_details['bank_name']} - {masked_account}"
                else:
                    display_name = f"Bank Account - {masked_account}"

            elif payment_type == "PAYPAL":
                # Validate PayPal details
                if not sanitized_details.get("email"):
                    raise PaymentServiceError(
                        "PayPal email address is required")

                # Create display name for PayPal
                display_name = f"PayPal - {sanitized_details['email']}"

            else:
                raise PaymentServiceError(
                    f"Unsupported payment method type: {payment_type}")

            # Create a new payment method token
            payment_method_id = str(uuid.uuid4())

            # In a real implementation, we would tokenize the sensitive payment data
            # and store only the token. For this example, we'll simulate that process.
            token_data = {
                "tokenized": True,
                "created": datetime.now().isoformat()
            }

            # Add non-sensitive fields directly
            for key, value in sanitized_details.items():
                if key not in ["account_number", "routing_number", "cvv"]:
                    token_data[key] = value

            # Create the payment method object
            new_payment_method = {
                "id": payment_method_id,
                "user_id": user["id"],
                "payment_type": payment_type,
                "token": token_data,
                "display_name": display_name,
                "is_default": False,  # It will be set to default if it's the first one
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # Get existing driver payment methods from user data
            driver_data = _get_driver_data_from_user(user["id"])
            existing_payment_methods = driver_data.get("payment_methods", [])

            # If this is the first payment method, make it the default
            if not existing_payment_methods:
                new_payment_method["is_default"] = True

            # Add the new payment method to the database
            response = requests.post(
                f"{BASE_URL}/payment_methods", json=new_payment_method)
            response.raise_for_status()
            created_payment_method = response.json()

            # Update the user's payment methods list
            if "payment_methods" not in driver_data:
                driver_data["payment_methods"] = []
            driver_data["payment_methods"].append(payment_method_id)

            # Save the updated user data
            update_response = requests.put(
                f"{BASE_URL}/users/{user['id']}", json=user)
            update_response.raise_for_status()

            # Return the created payment method
            return {
                "id": created_payment_method["id"],
                "payment_type": created_payment_method["payment_type"],
                "display_name": created_payment_method["display_name"],
                "is_default": created_payment_method["is_default"],
                "created_at": created_payment_method["created_at"],
                "updated_at": created_payment_method["updated_at"],
                **{key: value for key, value in token_data.items() if key not in ["tokenized", "created"]}
            }

        except requests.RequestException as e:
            raise PaymentServiceError(
                f"Failed to add payment method: {str(e)}")
        except AuthError:
            raise  # Re-throw auth errors without wrapping

    @staticmethod
    def get_driver_payment_methods(token: str) -> List[Dict[str, Any]]:
        """
        Get all payment methods for a driver to receive earnings.

        Args:
            token: JWT token for authentication (drivers only)

        Returns:
            List[Dict]: List of payment methods

        Raises:
            PaymentServiceError: If payment methods retrieval fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            user = AuthService.require_user_type(
                token, [UserType.DRIVER.value])

            # Get driver data from user ID to access the payment_methods list
            driver_data = _get_driver_data_from_user(user["id"])
            payment_method_ids = driver_data.get("payment_methods", [])

            if not payment_method_ids:
                return []

            # Fetch payment methods
            payment_methods = []
            for method_id in payment_method_ids:
                try:
                    response = requests.get(
                        f"{BASE_URL}/payment_methods/{method_id}")
                    if response.status_code == 200:
                        method = response.json()

                        # Create a safe version of the payment method to return
                        safe_method = {
                            "id": method["id"],
                            "payment_type": method["payment_type"],
                            "display_name": method["display_name"],
                            "is_default": method["is_default"],
                            "created_at": method["created_at"],
                            "updated_at": method["updated_at"]
                        }

                        # Add non-sensitive fields from the token
                        if "token" in method and isinstance(method["token"], dict):
                            for key, value in method["token"].items():
                                if key not in ["tokenized", "created"]:
                                    safe_method[key] = value

                        payment_methods.append(safe_method)
                except Exception:
                    # Skip any payment methods that can't be retrieved
                    continue

            return payment_methods

        except requests.RequestException as e:
            raise PaymentServiceError(
                f"Failed to retrieve payment methods: {str(e)}")
        except AuthError:
            raise  # Re-throw auth errors without wrapping

    @staticmethod
    def set_default_driver_payment_method(token: str, payment_method_id: str) -> Dict[str, Any]:
        """
        Set a payment method as the default for a driver to receive earnings.

        Args:
            token: JWT token for authentication (drivers only)
            payment_method_id: ID of the payment method to set as default

        Returns:
            Dict: The updated payment method

        Raises:
            PaymentServiceError: If setting default fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            user = AuthService.require_user_type(
                token, [UserType.DRIVER.value])

            # Get driver data from user ID to access the payment_methods list
            driver_data = _get_driver_data_from_user(user["id"])
            payment_method_ids = driver_data.get("payment_methods", [])

            if not payment_method_ids:
                raise PaymentServiceError("You don't have any payment methods")

            # Check if the specified payment method exists and belongs to this user
            if payment_method_id not in payment_method_ids:
                raise PaymentServiceError(
                    "Payment method not found or doesn't belong to you")

            # Update all payment methods
            for method_id in payment_method_ids:
                try:
                    # Get the payment method
                    response = requests.get(
                        f"{BASE_URL}/payment_methods/{method_id}")
                    if response.status_code != 200:
                        continue

                    method = response.json()

                    # Update is_default flag based on whether it matches the specified ID
                    method["is_default"] = (method_id == payment_method_id)
                    method["updated_at"] = datetime.now().isoformat()

                    # Save updated payment method
                    update_response = requests.put(
                        f"{BASE_URL}/payment_methods/{method_id}", json=method)
                    update_response.raise_for_status()

                    # If this is the one being set as default, remember it to return
                    if method_id == payment_method_id:
                        default_method = method
                except Exception:
                    # Continue with other payment methods if one fails
                    continue

            # Create a safe version of the payment method to return
            if 'default_method' not in locals():
                raise PaymentServiceError(
                    "Failed to set payment method as default")

            safe_method = {
                "id": default_method["id"],
                "payment_type": default_method["payment_type"],
                "display_name": default_method["display_name"],
                "is_default": default_method["is_default"],
                "created_at": default_method["created_at"],
                "updated_at": default_method["updated_at"]
            }

            # Add non-sensitive fields from the token
            if "token" in default_method and isinstance(default_method["token"], dict):
                for key, value in default_method["token"].items():
                    if key not in ["tokenized", "created"]:
                        safe_method[key] = value

            return safe_method

        except requests.RequestException as e:
            raise PaymentServiceError(
                f"Failed to set default payment method: {str(e)}")
        except AuthError:
            raise  # Re-throw auth errors without wrapping

    @staticmethod
    def remove_driver_payment_method(token: str, payment_method_id: str) -> bool:
        """
        Remove a payment method for a driver.

        Args:
            token: JWT token for authentication (drivers only)
            payment_method_id: ID of the payment method to remove

        Returns:
            bool: True if removal was successful

        Raises:
            PaymentServiceError: If removal fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            user = AuthService.require_user_type(
                token, [UserType.DRIVER.value])

            # Get driver data from user ID to access the payment_methods list
            driver_data = _get_driver_data_from_user(user["id"])
            payment_method_ids = driver_data.get("payment_methods", [])

            if not payment_method_ids:
                raise PaymentServiceError("You don't have any payment methods")

            # Check if the specified payment method exists and belongs to this user
            if payment_method_id not in payment_method_ids:
                raise PaymentServiceError(
                    "Payment method not found or doesn't belong to you")

            # Get the payment method to check if it's the default
            response = requests.get(
                f"{BASE_URL}/payment_methods/{payment_method_id}")
            if response.status_code != 200:
                raise PaymentServiceError("Failed to retrieve payment method")

            method_to_delete = response.json()
            is_default = method_to_delete.get("is_default", False)

            # Remove the payment method from the database
            delete_response = requests.delete(
                f"{BASE_URL}/payment_methods/{payment_method_id}")
            if delete_response.status_code not in [200, 204]:
                raise PaymentServiceError("Failed to delete payment method")

            # Remove the payment method ID from the user's list
            payment_method_ids.remove(payment_method_id)
            driver_data["payment_methods"] = payment_method_ids

            # Update the user data
            update_response = requests.put(
                f"{BASE_URL}/users/{user['id']}", json=user)
            update_response.raise_for_status()

            # If the deleted method was the default, set a new default if available
            if is_default and payment_method_ids:
                # Get the first available payment method
                new_default_id = payment_method_ids[0]
                PaymentService.set_default_driver_payment_method(
                    token, new_default_id)

            return True

        except requests.RequestException as e:
            raise PaymentServiceError(
                f"Failed to remove payment method: {str(e)}")
        except AuthError:
            raise  # Re-throw auth errors without wrapping

    @staticmethod
    def get_driver_payment_history(token: str, limit: int = 10, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get payment history for a driver.

        Args:
            token: JWT token for authentication (drivers only)
            limit: Maximum number of transactions to return
            from_date: Start date for filtering (ISO format)
            to_date: End date for filtering (ISO format)

        Returns:
            Dict: Payment history with transactions and summary

        Raises:
            PaymentServiceError: If retrieval fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            user = AuthService.require_user_type(
                token, [UserType.DRIVER.value])

            # Get all payments where the driver is the recipient
            response = requests.get(f"{BASE_URL}/payments")
            if response.status_code != 200:
                raise PaymentServiceError("Failed to retrieve payments")

            all_payments = response.json()

            # Filter payments for this driver
            driver_payments = [payment for payment in all_payments
                               if payment.get("recipient_id") == user["id"]]

            # Apply date filters if provided
            if from_date:
                driver_payments = [payment for payment in driver_payments
                                   if payment.get("timestamp", "") >= from_date]

            if to_date:
                driver_payments = [payment for payment in driver_payments
                                   if payment.get("timestamp", "") <= to_date]

            # Sort payments by timestamp (newest first)
            driver_payments.sort(key=lambda p: p.get(
                "timestamp", ""), reverse=True)

            # Limit the number of transactions
            limited_payments = driver_payments[:limit]

            # Prepare detailed transaction list
            transactions = []
            for payment in limited_payments:
                # Get payment method details
                payment_method = None
                if payment.get("payment_method_id"):
                    try:
                        method_response = requests.get(
                            f"{BASE_URL}/payment_methods/{payment['payment_method_id']}")
                        if method_response.status_code == 200:
                            method = method_response.json()
                            payment_method = {
                                "id": method["id"],
                                "display_name": method["display_name"],
                                "payment_type": method["payment_type"]
                            }
                    except Exception:
                        pass

                # Create transaction entry
                transactions.append({
                    "id": payment.get("id"),
                    "amount": payment.get("amount", 0),
                    "status": payment.get("status", "UNKNOWN"),
                    "timestamp": payment.get("timestamp", ""),
                    "ride_id": payment.get("ride_id", ""),
                    "payment_method": payment_method
                })

            # Calculate summary statistics
            total_earned = sum(payment.get("amount", 0) for payment in driver_payments
                               if payment.get("status") == "COMPLETED")

            pending_amount = sum(payment.get("amount", 0) for payment in driver_payments
                                 if payment.get("status") in ["PENDING", "PROCESSING"])

            # Return the payment history
            return {
                "total_earned": total_earned,
                "pending_amount": pending_amount,
                "transactions": transactions,
                "transaction_count": len(transactions)
            }

        except requests.RequestException as e:
            raise PaymentServiceError(
                f"Failed to retrieve payment history: {str(e)}")
        except AuthError:
            raise  # Re-throw auth errors without wrapping

    @staticmethod
    def process_ride_payment(ride_id: str, user_id: str, amount: float, payment_method_id: str, driver_id: str) -> Dict[str, Any]:
        """
        Process payment for a completed ride, including admin commission if applicable.

        Args:
            ride_id: ID of the ride
            user_id: ID of the user making the payment
            amount: Payment amount
            payment_method_id: ID of the payment method to use
            driver_id: ID of the driver to receive payment

        Returns:
            Dict: Payment details including commission data

        Raises:
            PaymentServiceError: If payment processing fails
        """
        try:
            # Check if commission is active
            try:
                commission_response = requests.get(f"{BASE_URL}/commissions/query?is_active=true")
                active_commissions = commission_response.json() if commission_response.status_code == 200 else []
                
                commission_active = bool(active_commissions)
            except:
                commission_active = False
                
            # Create main payment record
            payment_id = str(uuid.uuid4())
            payment = {
                "id": payment_id,
                "ride_id": ride_id,
                "user_id": user_id,
                "amount": amount,
                "payment_method_id": payment_method_id,
                "status": PaymentStatus.COMPLETED.value,
                "transaction_id": f"txn_{uuid.uuid4().hex[:10]}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_refunded": False
            }
            
            commission_data = None
            
            if commission_active and active_commissions:
                # Get the commission settings
                commission_setting = active_commissions[0]
                commission_percentage = float(commission_setting.get("percentage", 10.0)) / 100.0
                
                # Calculate commission and driver amounts
                commission_amount = round(amount * commission_percentage, 2)
                driver_amount = amount - commission_amount
                
                # Update the main payment with driver's portion
                payment["amount"] = driver_amount
                payment["driver_id"] = driver_id
                
                # Create commission payment record
                admin_id = commission_setting.get("admin_id")
                admin_payment_method_id = commission_setting.get("payment_method_id")
                
                if admin_id and admin_payment_method_id:
                    commission_payment_id = str(uuid.uuid4())
                    commission_payment = {
                        "id": commission_payment_id,
                        "ride_id": ride_id,
                        "user_id": user_id,
                        "admin_id": admin_id,
                        "amount": commission_amount,
                        "payment_method_id": admin_payment_method_id,
                        "status": PaymentStatus.COMPLETED.value,
                        "transaction_id": f"txn_comm_{uuid.uuid4().hex[:10]}",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "is_refunded": False,
                        "is_commission": True,
                        "original_payment_id": payment_id
                    }
                    
                    # Save commission payment
                    commission_response = requests.post(f"{BASE_URL}/payments", json=commission_payment)
                    commission_response.raise_for_status()
                    commission_data = commission_response.json()
            else:
                # No commission, the driver gets the full amount
                payment["driver_id"] = driver_id
            
            # Save the main payment
            response = requests.post(f"{BASE_URL}/payments", json=payment)
            response.raise_for_status()
            payment_data = response.json()
            
            # Update the ride with the payment information
            ride_response = requests.get(f"{BASE_URL}/rides/{ride_id}")
            if ride_response.status_code == 200:
                ride = ride_response.json()
                ride["payment_id"] = payment_id
                ride["status"] = RideStatus.COMPLETED.name
                ride["end_time"] = datetime.now().isoformat()
                ride["actual_fare"] = amount
                
                requests.put(f"{BASE_URL}/rides/{ride_id}", json=ride)
            
            # Prepare the response with payment and commission details
            result = {
                "payment": payment_data,
                "commission": commission_data
            }
            
            return result
            
        except requests.RequestException as e:
            raise PaymentServiceError(f"Failed to process payment: {str(e)}")

# Helper function to get driver data from user ID


def _get_driver_data_from_user(user_id: str) -> Dict[str, Any]:
    """Get driver-specific data from a user record."""
    try:
        # Get the user data
        response = requests.get(f"{BASE_URL}/users/{user_id}")
        if response.status_code != 200:
            raise PaymentServiceError("Failed to retrieve user data")

        user_data = response.json()

        # Return the driver data
        return user_data

    except requests.RequestException as e:
        raise PaymentServiceError(f"Failed to retrieve driver data: {str(e)}")


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

# Define the _sanitize_payment_details method to add to the payment service


def _sanitize_payment_details(payment_type: str, payment_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize and validate payment details based on the payment type.

    Args:
        payment_type: Type of payment method (e.g., BANK_ACCOUNT, PAYPAL, CREDIT_CARD)
        payment_details: Raw payment details from user input

    Returns:
        Dict: Sanitized payment details

    Raises:
        PaymentServiceError: If payment details are invalid or missing required fields
    """
    sanitized = {}

    if not payment_details:
        raise PaymentServiceError("Payment details cannot be empty")

    if payment_type == "BANK_ACCOUNT":
        # Required fields
        if "account_number" not in payment_details:
            raise PaymentServiceError(
                "Account number is required for bank account payments")
        if "routing_number" not in payment_details:
            raise PaymentServiceError(
                "Routing number is required for bank account payments")
        if "account_holder_name" not in payment_details:
            raise PaymentServiceError(
                "Account holder name is required for bank account payments")

        # Sanitize account number (numbers only)
        account_number = str(payment_details["account_number"]).replace(
            " ", "").replace("-", "")
        if not account_number.isdigit():
            raise PaymentServiceError(
                "Account number must contain only digits")
        if len(account_number) < 4 or len(account_number) > 17:
            raise PaymentServiceError(
                "Account number must be between 4 and 17 digits")

        # Sanitize routing number (9 digits for US banks)
        routing_number = str(payment_details["routing_number"]).replace(
            " ", "").replace("-", "")
        if not routing_number.isdigit():
            raise PaymentServiceError(
                "Routing number must contain only digits")
        if len(routing_number) != 9:
            raise PaymentServiceError("Routing number must be 9 digits")

        # Sanitize account holder name
        account_holder_name = str(
            payment_details["account_holder_name"]).strip()
        if len(account_holder_name) < 2 or len(account_holder_name) > 100:
            raise PaymentServiceError(
                "Account holder name must be between 2 and 100 characters")

        # Copy sanitized values
        sanitized["account_number"] = account_number
        sanitized["routing_number"] = routing_number
        sanitized["account_holder_name"] = account_holder_name

        # Optional bank name
        if "bank_name" in payment_details:
            bank_name = str(payment_details["bank_name"]).strip()
            if bank_name:  # Only add if not empty
                sanitized["bank_name"] = bank_name[:100]  # Limit length

    elif payment_type == "PAYPAL":
        # Required fields
        if "email" not in payment_details:
            raise PaymentServiceError("Email is required for PayPal payments")

        # Sanitize email
        email = str(payment_details["email"]).strip().lower()

        # Very basic email validation
        if "@" not in email or "." not in email or len(email) < 5:
            raise PaymentServiceError("Invalid email address format")

        sanitized["email"] = email

    elif payment_type == "CREDIT_CARD":
        # Required fields
        if "card_number" not in payment_details:
            raise PaymentServiceError(
                "Card number is required for credit card payments")
        if "expiry_month" not in payment_details:
            raise PaymentServiceError(
                "Expiry month is required for credit card payments")
        if "expiry_year" not in payment_details:
            raise PaymentServiceError(
                "Expiry year is required for credit card payments")
        if "cvv" not in payment_details:
            raise PaymentServiceError(
                "CVV is required for credit card payments")

        # Sanitize card number (numbers only)
        card_number = str(payment_details["card_number"]).replace(
            " ", "").replace("-", "")
        if not card_number.isdigit():
            raise PaymentServiceError("Card number must contain only digits")
        if len(card_number) < 13 or len(card_number) > 19:
            raise PaymentServiceError(
                "Card number must be between 13 and 19 digits")

        # Sanitize expiry month (1-12)
        try:
            expiry_month = int(payment_details["expiry_month"])
            if expiry_month < 1 or expiry_month > 12:
                raise PaymentServiceError(
                    "Expiry month must be between 1 and 12")
        except (ValueError, TypeError):
            raise PaymentServiceError("Expiry month must be a valid number")

        # Sanitize expiry year (current year or later)
        current_year = datetime.now().year
        try:
            expiry_year = int(payment_details["expiry_year"])
            if expiry_year < current_year or expiry_year > current_year + 20:
                raise PaymentServiceError(
                    f"Expiry year must be between {current_year} and {current_year + 20}")
        except (ValueError, TypeError):
            raise PaymentServiceError("Expiry year must be a valid number")

        # Check if card is already expired
        if expiry_year == current_year and expiry_month < datetime.now().month:
            raise PaymentServiceError("This card has already expired")

        # Sanitize CVV (3-4 digits)
        cvv = str(payment_details["cvv"]).strip()
        if not cvv.isdigit() or len(cvv) < 3 or len(cvv) > 4:
            raise PaymentServiceError("CVV must be 3 or 4 digits")

        # Copy sanitized values
        sanitized["card_number"] = card_number
        sanitized["expiry_month"] = expiry_month
        sanitized["expiry_year"] = expiry_year
        sanitized["cvv"] = cvv

        # Optional cardholder name
        if "cardholder_name" in payment_details:
            cardholder_name = str(payment_details["cardholder_name"]).strip()
            if cardholder_name:  # Only add if not empty
                # Limit length
                sanitized["cardholder_name"] = cardholder_name[:100]

        # Set expiry for display
        sanitized["expiry"] = f"{expiry_month:02d}/{expiry_year}"

    else:
        raise PaymentServiceError(f"Unsupported payment type: {payment_type}")

    return sanitized
