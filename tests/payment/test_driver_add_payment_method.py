"""
Test for driver payment commands.

This test:
1. Sets up test data (driver user, payment methods)
2. Tests all driver payment commands with various options
3. Validates the output format and content
"""

import os
import sys
import json
import unittest
import subprocess
import tempfile
import shutil
from datetime import datetime, timedelta
import requests
import time
import uuid
from unittest.mock import patch, MagicMock

# Add the project root to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.models.user import UserType
from app.services.auth_service import AuthService
from app.services.payment_service import PaymentService

# Constants for our test
BASE_URL = "http://localhost:3000"
DRIVER_EMAIL = "test.driver@example.com"
DRIVER_PASSWORD = "Driver123!"


class TestDriverPaymentCommands(unittest.TestCase):
    """Test the driver-payment command group."""

    @classmethod
    def setUpClass(cls):
        """Set up test data before running tests."""
        # Start the server in the background
        cls.start_server()
        
        # Create test config directory for storing auth token
        cls.config_dir = os.path.expanduser("~/.cabcab")
        os.makedirs(cls.config_dir, exist_ok=True)
        
        # Create test driver user
        cls.create_test_data()

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        # Stop the server
        cls.stop_server()
        
        # Clean up test data
        cls.clean_test_data()
        
        # Clean up config directory
        try:
            shutil.rmtree(cls.config_dir)
        except:
            pass

    @classmethod
    def start_server(cls):
        """Start the JSON server for testing."""
        print("Starting test server...")
        
        # Check if server is already running
        try:
            response = requests.get(f"{BASE_URL}")
            if response.status_code == 200:
                print("Server already running")
                return
        except:
            pass

        # Create data directory if it doesn't exist
        os.makedirs(os.path.join(os.path.dirname(__file__), '../../data'), exist_ok=True)
        
        # Create an empty database file
        db_path = os.path.join(os.path.dirname(__file__), '../../data/db.json')
        
        # Initialize the database with required collections
        with open(db_path, 'w') as f:
            json.dump({
                "users": [],
                "drivers": [],
                "vehicles": [],
                "locations": [],
                "rides": [],
                "payments": [],
                "payment_methods": []  # Important for our test
            }, f)
        
        # Start the server as a background process
        server_path = os.path.join(os.path.dirname(__file__), '../../test_server.py')
        
        # Use subprocess to start the server
        cls.server_process = subprocess.Popen(
            [sys.executable, server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give the server time to start
        time.sleep(2)
        
        # Check if server is running
        try:
            response = requests.get(f"{BASE_URL}")
            assert response.status_code == 200
            print("Test server started")
        except Exception as e:
            print(f"Failed to start test server: {e}")
            stdout, stderr = cls.server_process.communicate()
            print(f"Server stdout: {stdout.decode('utf-8')}")
            print(f"Server stderr: {stderr.decode('utf-8')}")
            cls.server_process.kill()
            raise Exception("Failed to start test server")

    @classmethod
    def stop_server(cls):
        """Stop the JSON server."""
        if hasattr(cls, 'server_process'):
            print("Stopping test server...")
            cls.server_process.terminate()
            cls.server_process.wait(timeout=5)
            print("Test server stopped")

    @classmethod
    def create_test_data(cls):
        """Create test driver user."""
        print("Creating test data...")
        
        # Create driver user
        driver_id = str(uuid.uuid4())
        driver = {
            "id": driver_id,
            "email": DRIVER_EMAIL,
            "password": "hashed_password",  # In real app, this would be hashed
            "first_name": "Test",
            "last_name": "Driver",
            "phone": "555-1234",
            "user_type": UserType.DRIVER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True,
            "is_verified": True,
            "is_available": True,
            "license_number": "DL12345678",
            "payment_methods": []  # Empty list for payment methods
        }
        
        # Save the driver to the database
        cls.post_data("users", driver)
        
        # Store the driver ID for later use
        cls.driver_id = driver_id
        
        print("Test driver created with ID:", driver_id)
    
    @classmethod
    def post_data(cls, collection, data):
        """Post data to the API."""
        response = requests.post(f"{BASE_URL}/{collection}", json=data)
        assert response.status_code == 201, f"Failed to create {collection}: {response.text}"
    
    @classmethod
    def clean_test_data(cls):
        """Clean up test data."""
        print("Cleaning up test data...")
        
        # Delete all records from all collections
        try:
            # Get current DB data
            response = requests.get(f"{BASE_URL}")
            if response.status_code == 200:
                db = response.json()
                
                # Clear collections
                for collection in ["payment_methods", "payments", "rides", "locations", "vehicles", "users"]:
                    if collection in db and db[collection]:
                        for item in db[collection]:
                            if "id" in item:
                                requests.delete(f"{BASE_URL}/{collection}/{item['id']}")
                
                # Verify collections are empty
                response = requests.get(f"{BASE_URL}")
                if response.status_code == 200:
                    db = response.json()
                    for collection in db:
                        assert len(db[collection]) == 0, f"{collection} not empty after cleanup"
        except Exception as e:
            print(f"Error cleaning up test data: {e}")
        
        print("Test data cleaned up")
    
    def login_as_driver(self):
        """Log in as driver and save token to config file."""
        # Mock the AuthService.login method to return a token without needing a real login
        with patch('app.services.auth_service.AuthService.login') as mock_login:
            driver_data = {
                "id": self.driver_id,
                "email": DRIVER_EMAIL,
                "first_name": "Test",
                "last_name": "Driver",
                "user_type": UserType.DRIVER.value,
                "payment_methods": []
            }
            
            # Create a token that will pass verification
            mock_token = "fake_driver_token"
            
            mock_login.return_value = {
                "token": mock_token,
                "user": driver_data
            }
            
            # Save token to config file
            with open(os.path.join(self.config_dir, "config.json"), 'w') as f:
                json.dump({"token": mock_token}, f)
            
            # Mock token verification to return the driver user
            with patch('app.services.auth_service.AuthService.verify_token') as mock_verify:
                mock_verify.return_value = driver_data
                
                # Mock the require_user_type method to allow driver
                with patch('app.services.auth_service.AuthService.require_user_type') as mock_require:
                    mock_require.return_value = driver_data
                    
                    # Return the patchers for later cleanup
                    return mock_login, mock_verify, mock_require
    
    def test_add_bank_account(self):
        """Test adding a bank account payment method."""
        # Login as driver
        mock_login, mock_verify, mock_require = self.login_as_driver()
        
        try:
            # Mock the PaymentService.add_driver_payment_method
            with patch('app.services.payment_service.PaymentService.add_driver_payment_method') as mock_add:
                # Set up the mock return value
                mock_add.return_value = {
                    "id": str(uuid.uuid4()),
                    "payment_type": "BANK_ACCOUNT",
                    "display_name": "Test Bank - ****5678",
                    "is_default": True,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "bank_name": "Test Bank"
                }
                
                # Create a temporary file to capture command output
                with tempfile.NamedTemporaryFile(mode='w+') as temp_input, \
                     tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                    
                    # Write the input values to the file
                    temp_input.write("Test Account Holder\n")  # account_holder_name
                    temp_input.write("123456789\n")  # account_number
                    temp_input.write("987654321\n")  # routing_number
                    temp_input.write("Test Bank\n")  # bank_name
                    temp_input.flush()
                    
                    # Prepare command to run
                    command = [
                        "python", "-c", 
                        "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.driver_payment_commands import add_driver_payment_method; add_driver_payment_method('bank-account')"
                    ]
                    
                    # Execute command with input file
                    process = subprocess.Popen(
                        command,
                        stdin=open(temp_input.name, 'r'),
                        stdout=temp_output,
                        stderr=subprocess.STDOUT,
                        cwd="/tmp/project"
                    )
                    process.wait()
                    
                    # Read output
                    temp_output.seek(0)
                    output = temp_output.read()
                    
                    # Verify output contains expected information
                    self.assertIn("Payment method added successfully", output)
                    self.assertIn("Test Bank", output)
                    
                    print("Test output:", output)
                    
                # Verify the method was called with correct parameters
                mock_add.assert_called_once()
                call_args = mock_add.call_args[0]
                self.assertEqual(call_args[1], "BANK_ACCOUNT")
                self.assertEqual(call_args[2]["account_holder_name"], "Test Account Holder")
                self.assertEqual(call_args[2]["account_number"], "123456789")
                self.assertEqual(call_args[2]["routing_number"], "987654321")
                self.assertEqual(call_args[2]["bank_name"], "Test Bank")
        
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_add_paypal(self):
        """Test adding a PayPal payment method."""
        # Login as driver
        mock_login, mock_verify, mock_require = self.login_as_driver()
        
        try:
            # Mock the PaymentService.add_driver_payment_method
            with patch('app.services.payment_service.PaymentService.add_driver_payment_method') as mock_add:
                # Set up the mock return value
                mock_add.return_value = {
                    "id": str(uuid.uuid4()),
                    "payment_type": "PAYPAL",
                    "display_name": "PayPal - driver@example.com",
                    "is_default": True,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "email": "driver@example.com"
                }
                
                # Create a temporary file to capture command output
                with tempfile.NamedTemporaryFile(mode='w+') as temp_input, \
                     tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                    
                    # Write the input values to the file
                    temp_input.write("driver@example.com\n")  # email
                    temp_input.flush()
                    
                    # Prepare command to run
                    command = [
                        "python", "-c", 
                        "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.driver_payment_commands import add_driver_payment_method; add_driver_payment_method('paypal')"
                    ]
                    
                    # Execute command with input file
                    process = subprocess.Popen(
                        command,
                        stdin=open(temp_input.name, 'r'),
                        stdout=temp_output,
                        stderr=subprocess.STDOUT,
                        cwd="/tmp/project"
                    )
                    process.wait()
                    
                    # Read output
                    temp_output.seek(0)
                    output = temp_output.read()
                    
                    # Verify output contains expected information
                    self.assertIn("Payment method added successfully", output)
                    self.assertIn("PayPal", output)
                    self.assertIn("driver@example.com", output)
                    
                    print("Test output:", output)
                    
                # Verify the method was called with correct parameters
                mock_add.assert_called_once()
                call_args = mock_add.call_args[0]
                self.assertEqual(call_args[1], "PAYPAL")
                self.assertEqual(call_args[2]["email"], "driver@example.com")
        
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_list_payment_methods(self):
        """Test listing payment methods."""
        # Login as driver
        mock_login, mock_verify, mock_require = self.login_as_driver()
        
        try:
            # Mock the PaymentService.get_driver_payment_methods
            with patch('app.services.payment_service.PaymentService.get_driver_payment_methods') as mock_get:
                # Set up the mock return value with multiple payment methods
                mock_get.return_value = [
                    {
                        "id": "pm_1",
                        "payment_type": "BANK_ACCOUNT",
                        "display_name": "Test Bank - ****5678",
                        "is_default": True,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "bank_name": "Test Bank"
                    },
                    {
                        "id": "pm_2",
                        "payment_type": "PAYPAL",
                        "display_name": "PayPal - driver@example.com",
                        "is_default": False,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "email": "driver@example.com"
                    }
                ]
                
                # Create a temporary file to capture command output
                with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                    # Prepare command to run
                    command = [
                        "python", "-c", 
                        "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.driver_payment_commands import list_driver_payment_methods; list_driver_payment_methods()"
                    ]
                    
                    # Execute command
                    process = subprocess.Popen(
                        command,
                        stdout=temp_output,
                        stderr=subprocess.STDOUT,
                        cwd="/tmp/project"
                    )
                    process.wait()
                    
                    # Read output
                    temp_output.seek(0)
                    output = temp_output.read()
                    
                    # Verify output contains expected information for both payment methods
                    self.assertIn("Your Earnings Payment Methods", output)
                    self.assertIn("Test Bank - ****5678", output)
                    self.assertIn("PayPal - driver@example.com", output)
                    self.assertIn("BANK_ACCOUNT", output)
                    self.assertIn("PAYPAL", output)
                    
                    # Verify the default indicator is shown
                    self.assertIn("✓", output)
                    
                    print("Test output:", output)
        
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_set_default_payment_method(self):
        """Test setting a payment method as default."""
        # Login as driver
        mock_login, mock_verify, mock_require = self.login_as_driver()
        
        try:
            # Mock the PaymentService.set_default_driver_payment_method
            with patch('app.services.payment_service.PaymentService.set_default_driver_payment_method') as mock_set:
                # Set up the mock return value
                mock_set.return_value = {
                    "id": "pm_2",
                    "payment_type": "PAYPAL",
                    "display_name": "PayPal - driver@example.com",
                    "is_default": True,  # Now set to default
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "email": "driver@example.com"
                }
                
                # Create a temporary file to capture command output
                with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                    # Prepare command to run
                    command = [
                        "python", "-c", 
                        "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.driver_payment_commands import set_default_driver_payment; set_default_driver_payment('pm_2')"
                    ]
                    
                    # Execute command
                    process = subprocess.Popen(
                        command,
                        stdout=temp_output,
                        stderr=subprocess.STDOUT,
                        cwd="/tmp/project"
                    )
                    process.wait()
                    
                    # Read output
                    temp_output.seek(0)
                    output = temp_output.read()
                    
                    # Verify output contains expected information
                    self.assertIn("set as your default payment method", output)
                    self.assertIn("PayPal - driver@example.com", output)
                    
                    print("Test output:", output)
                    
                # Verify the method was called with correct parameters
                mock_set.assert_called_once_with("fake_driver_token", "pm_2")
        
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_remove_payment_method(self):
        """Test removing a payment method."""
        # Login as driver
        mock_login, mock_verify, mock_require = self.login_as_driver()
        
        try:
            # First, mock get_driver_payment_methods to return the method details
            with patch('app.services.payment_service.PaymentService.get_driver_payment_methods') as mock_get:
                mock_get.return_value = [{
                    "id": "pm_1",
                    "payment_type": "BANK_ACCOUNT",
                    "display_name": "Test Bank - ****5678",
                    "is_default": True,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }]
                
                # Then, mock remove_driver_payment_method
                with patch('app.services.payment_service.PaymentService.remove_driver_payment_method') as mock_remove:
                    # Set up the mock return value
                    mock_remove.return_value = True
                    
                    # Create a temporary file to capture command output
                    with tempfile.NamedTemporaryFile(mode='w+') as temp_input, \
                         tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                        
                        # Write confirmation to input
                        temp_input.write("y\n")  # Confirm removal
                        temp_input.flush()
                        
                        # Prepare command to run
                        command = [
                            "python", "-c", 
                            "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.driver_payment_commands import remove_driver_payment_method; remove_driver_payment_method('pm_1', False)"
                        ]
                        
                        # Execute command with input file for confirmation
                        process = subprocess.Popen(
                            command,
                            stdin=open(temp_input.name, 'r'),
                            stdout=temp_output,
                            stderr=subprocess.STDOUT,
                            cwd="/tmp/project"
                        )
                        process.wait()
                        
                        # Read output
                        temp_output.seek(0)
                        output = temp_output.read()
                        
                        # Verify output contains expected information
                        self.assertIn("Payment method removed successfully", output)
                        
                        print("Test output:", output)
                        
                    # Verify the method was called with correct parameters
                    mock_remove.assert_called_once_with("fake_driver_token", "pm_1")
        
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_payment_history(self):
        """Test viewing payment history."""
        # Login as driver
        mock_login, mock_verify, mock_require = self.login_as_driver()
        
        try:
            # Mock the PaymentService.get_driver_payment_history
            with patch('app.services.payment_service.PaymentService.get_driver_payment_history') as mock_history:
                # Set up the mock return value
                payment_method = {
                    "id": "pm_1",
                    "display_name": "Test Bank - ****5678",
                    "payment_type": "BANK_ACCOUNT"
                }
                
                mock_history.return_value = {
                    "total_earned": 250.75,
                    "pending_amount": 50.25,
                    "transactions": [
                        {
                            "id": "tx_1",
                            "amount": 25.50,
                            "status": "COMPLETED",
                            "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
                            "ride_id": "ride_1",
                            "payment_method": payment_method
                        },
                        {
                            "id": "tx_2",
                            "amount": 32.75,
                            "status": "COMPLETED",
                            "timestamp": (datetime.now() - timedelta(days=3)).isoformat(),
                            "ride_id": "ride_2",
                            "payment_method": payment_method
                        },
                        {
                            "id": "tx_3",
                            "amount": 18.25,
                            "status": "PENDING",
                            "timestamp": datetime.now().isoformat(),
                            "ride_id": "ride_3",
                            "payment_method": payment_method
                        }
                    ],
                    "transaction_count": 3
                }
                
                # Create a temporary file to capture command output
                with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                    # Prepare command to run
                    command = [
                        "python", "-c", 
                        "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.driver_payment_commands import payment_history; payment_history(10, None, None)"
                    ]
                    
                    # Execute command
                    process = subprocess.Popen(
                        command,
                        stdout=temp_output,
                        stderr=subprocess.STDOUT,
                        cwd="/tmp/project"
                    )
                    process.wait()
                    
                    # Read output
                    temp_output.seek(0)
                    output = temp_output.read()
                    
                    # Verify output contains expected information
                    self.assertIn("Payment Summary", output)
                    self.assertIn("Total Earnings: $250.75", output)
                    self.assertIn("Pending Amount: $50.25", output)
                    self.assertIn("COMPLETED", output)
                    self.assertIn("PENDING", output)
                    self.assertIn("$25.50", output)
                    self.assertIn("Test Bank - ****5678", output)
                    
                    print("Test output:", output)
                    
                # Verify the method was called with correct parameters
                mock_history.assert_called_once_with("fake_driver_token", limit=10, from_date=None, to_date=None)
        
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_no_payment_methods(self):
        """Test list command when no payment methods exist."""
        # Login as driver
        mock_login, mock_verify, mock_require = self.login_as_driver()
        
        try:
            # Mock the PaymentService.get_driver_payment_methods to return empty list
            with patch('app.services.payment_service.PaymentService.get_driver_payment_methods') as mock_get:
                mock_get.return_value = []
                
                # Create a temporary file to capture command output
                with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                    # Prepare command to run
                    command = [
                        "python", "-c", 
                        "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.driver_payment_commands import list_driver_payment_methods; list_driver_payment_methods()"
                    ]
                    
                    # Execute command
                    process = subprocess.Popen(
                        command,
                        stdout=temp_output,
                        stderr=subprocess.STDOUT,
                        cwd="/tmp/project"
                    )
                    process.wait()
                    
                    # Read output
                    temp_output.seek(0)
                    output = temp_output.read()
                    
                    # Verify output contains expected information
                    self.assertIn("no payment methods", output.lower())
                    self.assertIn("add", output.lower())
                    
                    print("Test output:", output)
        
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()


if __name__ == '__main__':
    # Run the tests
    unittest.main()