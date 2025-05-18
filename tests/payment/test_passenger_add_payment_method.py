import unittest
import json
import uuid
import responses
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.services.payment_service import PaymentService, PaymentServiceError, MockCreditCardProcessor, MockPaypalProcessor
from app.services.auth_service import AuthService, UserType, JWT_SECRET, JWT_ALGORITHM
from click.testing import CliRunner
from app.cli_module.commands.payment_commands import add_payment_method


class TestAddPaymentMethod(unittest.TestCase):
    """Test suite for the passenger payment method addition functionality."""

    def setUp(self):
        """Set up test case with mock passenger user and token."""
        # Create a mock passenger user
        self.passenger_id = str(uuid.uuid4())
        self.passenger = {
            "id": self.passenger_id,
            "email": "passenger@example.com",
            "first_name": "Test",
            "last_name": "Passenger",
            "phone": "555-123-4567",
            "user_type": UserType.PASSENGER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "payment_methods": []
        }

        # Generate a valid JWT token for the passenger
        payload = {
            "user_id": self.passenger_id,
            "user_type": UserType.PASSENGER.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        self.token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Create a mock driver user (for testing user type validation)
        self.driver_id = str(uuid.uuid4())
        self.driver = {
            "id": self.driver_id,
            "email": "driver@example.com",
            "first_name": "Test",
            "last_name": "Driver",
            "user_type": UserType.DRIVER.value,
            "license_number": "DL12345678",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Generate a valid JWT token for the driver
        payload = {
            "user_id": self.driver_id,
            "user_type": UserType.DRIVER.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        self.driver_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Set up CLI runner for testing commands
        self.runner = CliRunner()
        
        # Start response mocking
        responses.start()

    def tearDown(self):
        """Clean up mocks after each test."""
        responses.stop()
        responses.reset()

    def _mock_token_file(self, token):
        """Helper method to mock token file for CLI commands."""
        config_dir = '/tmp/.cabcab'
        config_file = f"{config_dir}/config.json"
        
        import os
        os.makedirs(config_dir, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump({"token": token}, f)
            
        return config_file
        
    def _clean_token_file(self):
        """Clean up the mock token file."""
        config_file = '/tmp/.cabcab/config.json'
        
        import os
        if os.path.exists(config_file):
            os.remove(config_file)

    @responses.activate
    def test_add_credit_card_success(self):
        """Test successfully adding a credit card as a payment method."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=self.passenger,
            status=200
        )
        
        # Mock credit card details
        credit_card_details = {
            "card_number": "4111111111111111",
            "expiry_month": 12,
            "expiry_year": datetime.now().year + 2,
            "cvv": "123",
            "cardholder_name": "Test Passenger"
        }
        
        # Expected tokenized card
        card_token = {
            "token_id": responses.matchers.ANY,
            "card_type": "VISA",
            "last_four": "1111",
            "expiry_month": credit_card_details["expiry_month"],
            "expiry_year": credit_card_details["expiry_year"],
            "cardholder_name": credit_card_details["cardholder_name"],
            "masked_number": "xxxx-xxxx-xxxx-1111",
            "created_at": responses.matchers.ANY
        }
        
        # Expected payment method
        payment_method_id = str(uuid.uuid4())
        expected_payment_method = {
            "id": payment_method_id,
            "user_id": self.passenger_id,
            "payment_type": "CREDIT_CARD",
            "token": card_token,
            "card_type": "VISA",
            "last_four": "1111",
            "expiry": f"12/{credit_card_details['expiry_year']}",
            "display_name": "VISA ending in 1111",
            "is_default": True,  # First payment method becomes default
            "created_at": responses.matchers.ANY,
            "updated_at": responses.matchers.ANY
        }
        
        # Mock the payment method creation endpoint
        responses.add(
            responses.POST,
            "http://localhost:3000/payment_methods",
            json=expected_payment_method,
            status=201
        )
        
        # Mock the get payment methods endpoint (checking if this is the first one)
        responses.add(
            responses.GET,
            f"http://localhost:3000/payment_methods/query?user_id={self.passenger_id}",
            json=[expected_payment_method],
            status=200
        )
        
        # Mock update payment method endpoint (to make it default)
        responses.add(
            responses.PUT,
            f"http://localhost:3000/payment_methods/{payment_method_id}",
            json=expected_payment_method,
            status=200
        )
        
        # Mock update user endpoint (to add payment method to user's list)
        updated_passenger = self.passenger.copy()
        updated_passenger["payment_methods"] = [payment_method_id]
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=updated_passenger,
            status=200
        )
        
        # Execute the add payment method
        result = PaymentService.add_payment_method(
            self.token, 
            "CREDIT_CARD",
            credit_card_details
        )
        
        # Assert expected result
        self.assertEqual(result["payment_type"], "CREDIT_CARD")
        self.assertEqual(result["card_type"], "VISA")
        self.assertEqual(result["last_four"], "1111")
        self.assertEqual(result["display_name"], "VISA ending in 1111")
        self.assertTrue(result["is_default"])
        self.assertEqual(result["user_id"], self.passenger_id)

    @responses.activate
    def test_add_paypal_success(self):
        """Test successfully adding a PayPal account as a payment method."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=self.passenger,
            status=200
        )
        
        # Mock PayPal details
        paypal_details = {
            "email": "test.user@example.com"
        }
        
        # Expected tokenized PayPal
        paypal_token = {
            "token_id": responses.matchers.ANY,
            "email": paypal_details["email"],
            "account_type": "PAYPAL",
            "created_at": responses.matchers.ANY
        }
        
        # Expected payment method
        payment_method_id = str(uuid.uuid4())
        expected_payment_method = {
            "id": payment_method_id,
            "user_id": self.passenger_id,
            "payment_type": "PAYPAL",
            "token": paypal_token,
            "email": paypal_details["email"],
            "display_name": f"PayPal ({paypal_details['email']})",
            "is_default": True,  # First payment method becomes default
            "created_at": responses.matchers.ANY,
            "updated_at": responses.matchers.ANY
        }
        
        # Mock the payment method creation endpoint
        responses.add(
            responses.POST,
            "http://localhost:3000/payment_methods",
            json=expected_payment_method,
            status=201
        )
        
        # Mock the get payment methods endpoint (checking if this is the first one)
        responses.add(
            responses.GET,
            f"http://localhost:3000/payment_methods/query?user_id={self.passenger_id}",
            json=[expected_payment_method],
            status=200
        )
        
        # Mock update payment method endpoint (to make it default)
        responses.add(
            responses.PUT,
            f"http://localhost:3000/payment_methods/{payment_method_id}",
            json=expected_payment_method,
            status=200
        )
        
        # Mock update user endpoint (to add payment method to user's list)
        updated_passenger = self.passenger.copy()
        updated_passenger["payment_methods"] = [payment_method_id]
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=updated_passenger,
            status=200
        )
        
        # Execute the add payment method
        result = PaymentService.add_payment_method(
            self.token, 
            "PAYPAL",
            paypal_details
        )
        
        # Assert expected result
        self.assertEqual(result["payment_type"], "PAYPAL")
        self.assertEqual(result["email"], paypal_details["email"])
        self.assertEqual(result["display_name"], f"PayPal ({paypal_details['email']})")
        self.assertTrue(result["is_default"])
        self.assertEqual(result["user_id"], self.passenger_id)

    @responses.activate
    def test_add_payment_method_non_passenger(self):
        """Test that drivers cannot add payment methods."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock credit card details
        credit_card_details = {
            "card_number": "4111111111111111",
            "expiry_month": 12,
            "expiry_year": datetime.now().year + 2,
            "cvv": "123",
            "cardholder_name": "Test Driver"
        }
        
        # Assert that drivers cannot add payment methods
        with self.assertRaises(Exception) as context:
            PaymentService.add_payment_method(
                self.driver_token, 
                "CREDIT_CARD",
                credit_card_details
            )
        
        self.assertIn("access denied", str(context.exception).lower())

    @responses.activate
    def test_add_payment_method_invalid_card(self):
        """Test handling invalid credit card details."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=self.passenger,
            status=200
        )
        
        # Mock invalid credit card details (expired)
        invalid_card_details = {
            "card_number": "4111111111111111",
            "expiry_month": 1,
            "expiry_year": 2000,  # Expired card
            "cvv": "123",
            "cardholder_name": "Test Passenger"
        }
        
        # Assert that adding an invalid card fails
        with self.assertRaises(PaymentServiceError) as context:
            PaymentService.add_payment_method(
                self.token, 
                "CREDIT_CARD",
                invalid_card_details
            )
        
        self.assertIn("invalid credit card", str(context.exception).lower())
        
        # Test another type of invalid card (non-numeric)
        invalid_card_details["expiry_year"] = datetime.now().year + 2
        invalid_card_details["card_number"] = "41111-INVALID-1111"
        
        with self.assertRaises(PaymentServiceError) as context:
            PaymentService.add_payment_method(
                self.token, 
                "CREDIT_CARD",
                invalid_card_details
            )
        
        self.assertIn("invalid credit card", str(context.exception).lower())

    @responses.activate
    def test_add_payment_method_invalid_paypal(self):
        """Test handling invalid PayPal details."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=self.passenger,
            status=200
        )
        
        # Mock invalid PayPal details
        invalid_paypal_details = {
            "email": "not.an.email"  # Invalid email format
        }
        
        # Assert that adding an invalid PayPal account fails
        with self.assertRaises(PaymentServiceError) as context:
            PaymentService.add_payment_method(
                self.token, 
                "PAYPAL",
                invalid_paypal_details
            )
        
        self.assertIn("invalid paypal account", str(context.exception).lower())

    @responses.activate
    def test_add_payment_method_unsupported_type(self):
        """Test handling unsupported payment method types."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=self.passenger,
            status=200
        )
        
        # Mock invalid payment method type
        unavailable_payment_details = {
            "account_id": "1234567890"
        }
        
        # Assert that adding an unsupported payment type fails
        with self.assertRaises(PaymentServiceError) as context:
            PaymentService.add_payment_method(
                self.token, 
                "BITCOIN",
                unavailable_payment_details
            )
        
        self.assertIn("unsupported payment type", str(context.exception).lower())

    @responses.activate
    def test_add_payment_method_unauthenticated(self):
        """Test handling unauthenticated users."""
        # Use an invalid token
        invalid_token = "invalid-token-123"
        
        # Mock invalid token validation
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/me",
            status=401,
            json={"error": "Invalid token"}
        )
        
        # Mock credit card details
        credit_card_details = {
            "card_number": "4111111111111111",
            "expiry_month": 12,
            "expiry_year": datetime.now().year + 2,
            "cvv": "123",
            "cardholder_name": "Test Passenger"
        }
        
        # Assert that unauthenticated users cannot add payment methods
        with self.assertRaises(Exception) as context:
            PaymentService.add_payment_method(
                invalid_token, 
                "CREDIT_CARD",
                credit_card_details
            )
        
        self.assertIn("token", str(context.exception).lower())

    @responses.activate
    def test_add_payment_method_server_error(self):
        """Test handling server errors."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=self.passenger,
            status=200
        )
        
        # Mock credit card details
        credit_card_details = {
            "card_number": "4111111111111111",
            "expiry_month": 12,
            "expiry_year": datetime.now().year + 2,
            "cvv": "123",
            "cardholder_name": "Test Passenger"
        }
        
        # Mock the payment method creation endpoint with server error
        responses.add(
            responses.POST,
            "http://localhost:3000/payment_methods",
            status=500,
            json={"error": "Internal server error"}
        )
        
        # Assert that server errors are handled
        with self.assertRaises(PaymentServiceError) as context:
            PaymentService.add_payment_method(
                self.token, 
                "CREDIT_CARD",
                credit_card_details
            )
        
        self.assertIn("failed to add payment method", str(context.exception).lower())

    @responses.activate
    @patch('click.prompt')
    def test_cli_add_credit_card_command(self, mock_prompt):
        """Test the CLI command for adding a credit card payment method."""
        # Mock the token file
        self._mock_token_file(self.token)
        
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=self.passenger,
            status=200
        )
        
        # Set up prompt mock returns for credit card details
        mock_prompt.side_effect = [
            "4111111111111111",  # Card number
            "12",                # Expiry month
            "2030",              # Expiry year
            "123",               # CVV
            "Test Passenger"     # Cardholder name
        ]
        
        # Expected tokenized card
        card_token = {
            "token_id": responses.matchers.ANY,
            "card_type": "VISA",
            "last_four": "1111",
            "expiry_month": 12,
            "expiry_year": 2030,
            "cardholder_name": "Test Passenger",
            "masked_number": "xxxx-xxxx-xxxx-1111",
            "created_at": responses.matchers.ANY
        }
        
        # Expected payment method
        payment_method_id = str(uuid.uuid4())
        expected_payment_method = {
            "id": payment_method_id,
            "user_id": self.passenger_id,
            "payment_type": "CREDIT_CARD",
            "token": card_token,
            "card_type": "VISA",
            "last_four": "1111",
            "expiry": "12/2030",
            "display_name": "VISA ending in 1111",
            "is_default": True,  # First payment method becomes default
            "created_at": responses.matchers.ANY,
            "updated_at": responses.matchers.ANY
        }
        
        # Mock the payment method creation endpoint
        responses.add(
            responses.POST,
            "http://localhost:3000/payment_methods",
            json=expected_payment_method,
            status=201
        )
        
        # Mock the get payment methods endpoint (checking if this is the first one)
        responses.add(
            responses.GET,
            f"http://localhost:3000/payment_methods/query?user_id={self.passenger_id}",
            json=[expected_payment_method],
            status=200
        )
        
        # Mock update payment method endpoint (to make it default)
        responses.add(
            responses.PUT,
            f"http://localhost:3000/payment_methods/{payment_method_id}",
            json=expected_payment_method,
            status=200
        )
        
        # Mock update user endpoint (to add payment method to user's list)
        updated_passenger = self.passenger.copy()
        updated_passenger["payment_methods"] = [payment_method_id]
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=updated_passenger,
            status=200
        )
        
        # Run the CLI command
        result = self.runner.invoke(add_payment_method, ["--type", "credit-card"])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command ran successfully
        self.assertEqual(0, result.exit_code, f"Command failed with: {result.output}")
        
        # Check output contains success message
        self.assertIn("Payment method added successfully", result.output)
        self.assertIn("VISA", result.output)
        self.assertIn("1111", result.output)

    @responses.activate
    @patch('click.prompt')
    def test_cli_add_paypal_command(self, mock_prompt):
        """Test the CLI command for adding a PayPal payment method."""
        # Mock the token file
        self._mock_token_file(self.token)
        
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=self.passenger,
            status=200
        )
        
        # Set up prompt mock return for PayPal email
        paypal_email = "test.user@example.com"
        mock_prompt.return_value = paypal_email
        
        # Expected tokenized PayPal
        paypal_token = {
            "token_id": responses.matchers.ANY,
            "email": paypal_email,
            "account_type": "PAYPAL",
            "created_at": responses.matchers.ANY
        }
        
        # Expected payment method
        payment_method_id = str(uuid.uuid4())
        expected_payment_method = {
            "id": payment_method_id,
            "user_id": self.passenger_id,
            "payment_type": "PAYPAL",
            "token": paypal_token,
            "email": paypal_email,
            "display_name": f"PayPal ({paypal_email})",
            "is_default": True,  # First payment method becomes default
            "created_at": responses.matchers.ANY,
            "updated_at": responses.matchers.ANY
        }
        
        # Mock the payment method creation endpoint
        responses.add(
            responses.POST,
            "http://localhost:3000/payment_methods",
            json=expected_payment_method,
            status=201
        )
        
        # Mock the get payment methods endpoint (checking if this is the first one)
        responses.add(
            responses.GET,
            f"http://localhost:3000/payment_methods/query?user_id={self.passenger_id}",
            json=[expected_payment_method],
            status=200
        )
        
        # Mock update payment method endpoint (to make it default)
        responses.add(
            responses.PUT,
            f"http://localhost:3000/payment_methods/{payment_method_id}",
            json=expected_payment_method,
            status=200
        )
        
        # Mock update user endpoint (to add payment method to user's list)
        updated_passenger = self.passenger.copy()
        updated_passenger["payment_methods"] = [payment_method_id]
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=updated_passenger,
            status=200
        )
        
        # Run the CLI command
        result = self.runner.invoke(add_payment_method, ["--type", "paypal"])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command ran successfully
        self.assertEqual(0, result.exit_code, f"Command failed with: {result.output}")
        
        # Check output contains success message
        self.assertIn("Payment method added successfully", result.output)
        self.assertIn("PayPal", result.output)
        self.assertIn(paypal_email, result.output)

    def test_mock_credit_card_processor_validation(self):
        """Test the credit card validation in the mock processor."""
        processor = MockCreditCardProcessor()
        
        # Test valid card
        self.assertTrue(processor.validate_card(
            "4111111111111111", 12, datetime.now().year + 1, "123"
        ))
        
        # Test invalid card number (non-numeric)
        self.assertFalse(processor.validate_card(
            "4111-aaaa-1111-1111", 12, datetime.now().year + 1, "123"
        ))
        
        # Test expired card
        self.assertFalse(processor.validate_card(
            "4111111111111111", 1, 2000, "123"
        ))
        
        # Test invalid month
        self.assertFalse(processor.validate_card(
            "4111111111111111", 13, datetime.now().year + 1, "123"
        ))
        
        # Test invalid CVV
        self.assertFalse(processor.validate_card(
            "4111111111111111", 12, datetime.now().year + 1, "12345"
        ))

    def test_mock_paypal_processor_validation(self):
        """Test the PayPal account validation in the mock processor."""
        processor = MockPaypalProcessor()
        
        # Test valid email
        self.assertTrue(processor.validate_account("test.user@example.com"))
        
        # Test invalid email (no @)
        self.assertFalse(processor.validate_account("test.user.example.com"))
        
        # Test invalid email (no domain)
        self.assertFalse(processor.validate_account("test.user@"))


if __name__ == '__main__':
    unittest.main()