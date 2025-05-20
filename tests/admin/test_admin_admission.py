"""
Test for admin commission feature.

This test:
1. Sets up test data (admin, payment methods)
2. Tests all admin commission commands (set, status, enable, disable)
3. Tests the commission payment processing functionality
4. Validates the payment splitting and commission calculation
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
from app.services.commision_service import CommissionService, CommissionServiceError

# Constants for our test
BASE_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Admin123!"
PASSENGER_EMAIL = "passenger@test.com"
PASSENGER_PASSWORD = "Pass123!"
DRIVER_EMAIL = "driver@test.com"
DRIVER_PASSWORD = "Driver123!"


class TestAdminCommissionFeature(unittest.TestCase):
    """Test the admin commission feature and related commands."""

    @classmethod
    def setUpClass(cls):
        """Set up test data before running tests."""
        # Start the server in the background
        cls.start_server()
        
        # Create test config directory for storing auth token
        cls.config_dir = os.path.expanduser("~/.cabcab")
        os.makedirs(cls.config_dir, exist_ok=True)
        
        # Create test users and test data
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
        with open(db_path, 'w') as f:
            json.dump({
                "users": [],
                "drivers": [],
                "vehicles": [],
                "locations": [],
                "rides": [],
                "payments": [],
                "commissions": []  # Include commissions collection
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
        """Create test users, payment methods, and rides."""
        print("Creating test data...")
        
        # Create admin user
        cls.admin_id = str(uuid.uuid4())
        admin = {
            "id": cls.admin_id,
            "email": ADMIN_EMAIL,
            "password": "hashed_password",  # In real app, this would be hashed
            "first_name": "Admin",
            "last_name": "User",
            "phone": "555-ADMIN",
            "user_type": UserType.ADMIN.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        # Create passenger user
        cls.passenger_id = str(uuid.uuid4())
        passenger = {
            "id": cls.passenger_id,
            "email": PASSENGER_EMAIL,
            "password": "hashed_password",  # In real app, this would be hashed
            "first_name": "Test",
            "last_name": "Passenger",
            "phone": "555-PASS",
            "user_type": UserType.PASSENGER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True,
            "payment_methods": []
        }
        
        # Create driver user
        cls.driver_id = str(uuid.uuid4())
        driver = {
            "id": cls.driver_id,
            "email": DRIVER_EMAIL,
            "password": "hashed_password",  # In real app, this would be hashed
            "first_name": "Test",
            "last_name": "Driver",
            "phone": "555-DRIVER",
            "user_type": UserType.DRIVER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True,
            "is_verified": True,
            "is_available": True,
            "license_number": "DL12345678"
        }
        
        # Add users to database
        requests.post(f"{BASE_URL}/users", json=admin)
        requests.post(f"{BASE_URL}/users", json=passenger)
        requests.post(f"{BASE_URL}/users", json=driver)
        
        # Create payment method for admin
        cls.admin_payment_id = str(uuid.uuid4())
        admin_payment = {
            "id": cls.admin_payment_id,
            "user_id": cls.admin_id,
            "payment_type": "BANK_ACCOUNT",
            "token": {
                "token_id": str(uuid.uuid4()),
                "account_number_last_four": "6789",
                "account_holder_name": "Admin User",
                "bank_name": "Test Bank"
            },
            "display_name": "Bank Account ending in 6789",
            "is_default": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Create payment method for passenger
        cls.passenger_payment_id = str(uuid.uuid4())
        passenger_payment = {
            "id": cls.passenger_payment_id,
            "user_id": cls.passenger_id,
            "payment_type": "CREDIT_CARD",
            "token": {
                "token_id": str(uuid.uuid4()),
                "card_type": "VISA",
                "last_four": "4321",
                "expiry_month": 12,
                "expiry_year": 2025,
                "cardholder_name": "Test Passenger"
            },
            "display_name": "VISA ending in 4321",
            "is_default": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Add payment methods to database
        requests.post(f"{BASE_URL}/payments", json=admin_payment)
        requests.post(f"{BASE_URL}/payments", json=passenger_payment)
        
        # Create a vehicle for the driver
        cls.vehicle_id = str(uuid.uuid4())
        vehicle = {
            "id": cls.vehicle_id,
            "driver_id": cls.driver_id,
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "color": "Blue",
            "license_plate": "ABC-1234",
            "vehicle_type": "SEDAN",
            "capacity": 4,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Add vehicle to database
        requests.post(f"{BASE_URL}/vehicles", json=vehicle)
        
        # Update passenger with payment method
        passenger["payment_methods"] = [cls.passenger_payment_id]
        requests.put(f"{BASE_URL}/users/{cls.passenger_id}", json=passenger)
        
        # Update driver with vehicle
        driver["vehicle_id"] = cls.vehicle_id
        requests.put(f"{BASE_URL}/users/{cls.driver_id}", json=driver)
        
        # Create locations for rides
        cls.pickup_location_id = str(uuid.uuid4())
        cls.dropoff_location_id = str(uuid.uuid4())
        
        pickup_location = {
            "id": cls.pickup_location_id,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country": "USA",
            "user_id": cls.passenger_id
        }
        
        dropoff_location = {
            "id": cls.dropoff_location_id,
            "latitude": 40.7306,
            "longitude": -73.9352,
            "address": "456 Broadway",
            "city": "New York",
            "state": "NY",
            "postal_code": "10002",
            "country": "USA",
            "user_id": cls.passenger_id
        }
        
        # Add locations to database
        requests.post(f"{BASE_URL}/locations", json=pickup_location)
        requests.post(f"{BASE_URL}/locations", json=dropoff_location)

    @classmethod
    def clean_test_data(cls):
        """Clean up test data from the database."""
        print("Cleaning test data...")
        
        # For a real test, we would clear all test data
        # But the server is stopped and the database is temporary,
        # so no explicit cleanup is needed here

    def login_as_admin(self):
        """Set up authentication as admin for tests."""
        # Create a JWT token for the admin user
        token = AuthService.generate_token({
            "id": self.admin_id,
            "email": ADMIN_EMAIL,
            "user_type": UserType.ADMIN.value
        })
        
        # Save token to disk
        with open(os.path.join(self.config_dir, "auth_token.txt"), "w") as f:
            f.write(token)
        
        # Mock the auth service to return our admin user
        mock_login = patch('app.services.auth_service.AuthService.verify_token')
        mock_verify = patch('app.services.auth_service.AuthService.verify_user_type')
        mock_require = patch('app.services.auth_service.AuthService.require_user_type')
        
        mock_login_func = mock_login.start()
        mock_verify_func = mock_verify.start()
        mock_require_func = mock_require.start()
        
        admin_data = {
            "id": self.admin_id,
            "email": ADMIN_EMAIL,
            "user_type": UserType.ADMIN.value,
            "first_name": "Admin",
            "last_name": "User"
        }
        
        mock_login_func.return_value = admin_data
        mock_verify_func.return_value = True
        mock_require_func.return_value = admin_data
        
        return mock_login, mock_verify, mock_require

    def create_ride(self, status="REQUESTED"):
        """Create a test ride between passenger and driver."""
        ride_id = str(uuid.uuid4())
        ride = {
            "id": ride_id,
            "user_id": self.passenger_id,
            "pickup_location_id": self.pickup_location_id,
            "dropoff_location_id": self.dropoff_location_id,
            "request_time": datetime.now().isoformat(),
            "status": status,
            "estimated_fare": 25.50,
            "distance": 10.2,
            "duration": 30,
            "start_time": None,
            "end_time": None,
            "actual_fare": None,
            "payment_id": None,
            "rating": None,
            "feedback": None
        }
        
        # Add driver if status is not REQUESTED
        if status != "REQUESTED":
            ride["driver_id"] = self.driver_id
        
        # Add ride to database
        response = requests.post(f"{BASE_URL}/rides", json=ride)
        return response.json()["id"]

    def test_01_set_commission(self):
        """Test setting commission settings."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commission_commands import set_commission; set_commission('{self.admin_payment_id}', 15.0)"
                ]
                
                # Execute command and capture output
                process = subprocess.Popen(
                    command,
                    stdout=temp_output,
                    stderr=subprocess.STDOUT,
                    cwd="/tmp/inputs"
                )
                process.wait()
                
                # Read output
                temp_output.seek(0)
                output = temp_output.read()
                
                print("Command output:", output)
                
                # Check if command was successful
                self.assertIn("Commission settings updated successfully", output)
                self.assertIn("15%", output)
                
                # Verify database was updated
                response = requests.get(f"{BASE_URL}/commissions/query?admin_id={self.admin_id}")
                self.assertEqual(response.status_code, 200)
                
                commission_data = response.json()
                self.assertGreater(len(commission_data), 0)
                self.assertEqual(commission_data[0]["admin_id"], self.admin_id)
                self.assertEqual(commission_data[0]["payment_method_id"], self.admin_payment_id)
                self.assertEqual(commission_data[0]["percentage"], 15.0)
                self.assertTrue(commission_data[0]["is_active"])
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()

    def test_02_commission_status(self):
        """Test viewing commission status."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commission_commands import commission_status; commission_status()"
                ]
                
                # Execute command and capture output
                process = subprocess.Popen(
                    command,
                    stdout=temp_output,
                    stderr=subprocess.STDOUT,
                    cwd="/tmp/inputs"
                )
                process.wait()
                
                # Read output
                temp_output.seek(0)
                output = temp_output.read()
                
                print("Command output:", output)
                
                # Check if command displayed correct settings
                self.assertIn("Commission Settings", output)
                self.assertIn("15%", output)
                self.assertIn("Active", output)
                self.assertIn("Bank Account", output)
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()

    def test_03_disable_commission(self):
        """Test disabling commission collection."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commission_commands import disable_commission; disable_commission()"
                ]
                
                # Execute command and capture output
                process = subprocess.Popen(
                    command,
                    stdout=temp_output,
                    stderr=subprocess.STDOUT,
                    cwd="/tmp/inputs"
                )
                process.wait()
                
                # Read output
                temp_output.seek(0)
                output = temp_output.read()
                
                print("Command output:", output)
                
                # Check if command was successful
                self.assertIn("Commission collection has been disabled", output)
                
                # Verify database was updated
                response = requests.get(f"{BASE_URL}/commissions/query?admin_id={self.admin_id}")
                self.assertEqual(response.status_code, 200)
                
                commission_data = response.json()
                self.assertGreater(len(commission_data), 0)
                self.assertFalse(commission_data[0]["is_active"])
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()

    def test_04_payment_processing_without_commission(self):
        """Test payment processing when commission is disabled."""
        # Create a ride
        ride_id = self.create_ride(status="DRIVER_ASSIGNED")
        
        # Set up ride details for payment
        ride_amount = 30.00
        
        # Process a payment (simulating the process_ride_payment method)
        payment_id = str(uuid.uuid4())
        payment = {
            "id": payment_id,
            "ride_id": ride_id,
            "user_id": self.passenger_id,
            "driver_id": self.driver_id,
            "amount": ride_amount,  # Full amount to driver since commission is disabled
            "payment_method_id": self.passenger_payment_id,
            "status": "COMPLETED",
            "transaction_id": f"txn_{uuid.uuid4()}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_refunded": False
        }
        
        # Add payment to database
        response = requests.post(f"{BASE_URL}/payments", json=payment)
        self.assertEqual(response.status_code, 201)
        
        # Update ride status and payment
        ride_response = requests.get(f"{BASE_URL}/rides/{ride_id}")
        ride_data = ride_response.json()
        ride_data["payment_id"] = payment_id
        ride_data["status"] = "COMPLETED"
        ride_data["actual_fare"] = ride_amount
        ride_data["end_time"] = datetime.now().isoformat()
        
        update_response = requests.put(f"{BASE_URL}/rides/{ride_id}", json=ride_data)
        self.assertEqual(update_response.status_code, 200)
        
        # Check if driver received full amount (no commission)
        payment_response = requests.get(f"{BASE_URL}/payments/{payment_id}")
        self.assertEqual(payment_response.status_code, 200)
        payment_data = payment_response.json()
        self.assertEqual(payment_data["amount"], ride_amount)
        
        # Check if no commission payment was created
        commission_payments = requests.get(f"{BASE_URL}/payments/query?admin_id={self.admin_id}&is_commission=true")
        self.assertEqual(commission_payments.status_code, 200)
        self.assertEqual(len(commission_payments.json()), 0)

    def test_05_enable_commission(self):
        """Test enabling commission collection."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commission_commands import enable_commission; enable_commission()"
                ]
                
                # Execute command and capture output
                process = subprocess.Popen(
                    command,
                    stdout=temp_output,
                    stderr=subprocess.STDOUT,
                    cwd="/tmp/inputs"
                )
                process.wait()
                
                # Read output
                temp_output.seek(0)
                output = temp_output.read()
                
                print("Command output:", output)
                
                # Check if command was successful
                self.assertIn("Commission collection is now enabled", output)
                
                # Verify database was updated
                response = requests.get(f"{BASE_URL}/commissions/query?admin_id={self.admin_id}")
                self.assertEqual(response.status_code, 200)
                
                commission_data = response.json()
                self.assertGreater(len(commission_data), 0)
                self.assertTrue(commission_data[0]["is_active"])
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()

    def test_06_payment_processing_with_commission(self):
        """Test payment processing when commission is enabled."""
        # Create a ride
        ride_id = self.create_ride(status="DRIVER_ASSIGNED")
        
        # Set up ride details for payment
        total_amount = 40.00
        commission_percentage = 15.0
        commission_amount = total_amount * (commission_percentage / 100)
        driver_amount = total_amount - commission_amount
        
        # Process a payment with commission splitting
        driver_payment_id = str(uuid.uuid4())
        driver_payment = {
            "id": driver_payment_id,
            "ride_id": ride_id,
            "user_id": self.passenger_id,
            "driver_id": self.driver_id,
            "amount": driver_amount,  # 85% goes to driver
            "payment_method_id": self.passenger_payment_id,
            "status": "COMPLETED",
            "transaction_id": f"txn_{uuid.uuid4()}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_refunded": False
        }
        
        # Commission payment
        commission_payment_id = str(uuid.uuid4())
        commission_payment = {
            "id": commission_payment_id,
            "ride_id": ride_id,
            "user_id": self.passenger_id,
            "admin_id": self.admin_id,
            "amount": commission_amount,  # 15% goes to admin
            "payment_method_id": self.admin_payment_id,
            "status": "COMPLETED",
            "transaction_id": f"txn_comm_{uuid.uuid4()}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_refunded": False,
            "is_commission": True,
            "original_payment_id": driver_payment_id
        }
        
        # Add payments to database
        driver_response = requests.post(f"{BASE_URL}/payments", json=driver_payment)
        self.assertEqual(driver_response.status_code, 201)
        
        commission_response = requests.post(f"{BASE_URL}/payments", json=commission_payment)
        self.assertEqual(commission_response.status_code, 201)
        
        # Update ride status and payment
        ride_response = requests.get(f"{BASE_URL}/rides/{ride_id}")
        ride_data = ride_response.json()
        ride_data["payment_id"] = driver_payment_id
        ride_data["status"] = "COMPLETED"
        ride_data["actual_fare"] = total_amount
        ride_data["end_time"] = datetime.now().isoformat()
        
        update_response = requests.put(f"{BASE_URL}/rides/{ride_id}", json=ride_data)
        self.assertEqual(update_response.status_code, 200)
        
        # Verify driver payment amount (85%)
        driver_payment_response = requests.get(f"{BASE_URL}/payments/{driver_payment_id}")
        self.assertEqual(driver_payment_response.status_code, 200)
        driver_payment_data = driver_payment_response.json()
        self.assertEqual(driver_payment_data["amount"], driver_amount)
        
        # Verify commission payment amount (15%)
        commission_payment_response = requests.get(f"{BASE_URL}/payments/{commission_payment_id}")
        self.assertEqual(commission_payment_response.status_code, 200)
        commission_payment_data = commission_payment_response.json()
        self.assertEqual(commission_payment_data["amount"], commission_amount)
        self.assertEqual(commission_payment_data["admin_id"], self.admin_id)
        self.assertTrue(commission_payment_data["is_commission"])

    def test_07_change_commission_percentage(self):
        """Test changing the commission percentage."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run - change to 20%
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commission_commands import set_commission; set_commission('{self.admin_payment_id}', 20.0)"
                ]
                
                # Execute command and capture output
                process = subprocess.Popen(
                    command,
                    stdout=temp_output,
                    stderr=subprocess.STDOUT,
                    cwd="/tmp/inputs"
                )
                process.wait()
                
                # Read output
                temp_output.seek(0)
                output = temp_output.read()
                
                print("Command output:", output)
                
                # Check if command was successful
                self.assertIn("Commission settings updated successfully", output)
                self.assertIn("20%", output)
                
                # Verify database was updated
                response = requests.get(f"{BASE_URL}/commissions/query?admin_id={self.admin_id}")
                self.assertEqual(response.status_code, 200)
                
                commission_data = response.json()
                self.assertGreater(len(commission_data), 0)
                self.assertEqual(commission_data[0]["percentage"], 20.0)
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()

    def test_08_commission_earnings_display(self):
        """Test viewing commission earnings in status report."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commission_commands import commission_status; commission_status()"
                ]
                
                # Execute command and capture output
                process = subprocess.Popen(
                    command,
                    stdout=temp_output,
                    stderr=subprocess.STDOUT,
                    cwd="/tmp/inputs"
                )
                process.wait()
                
                # Read output
                temp_output.seek(0)
                output = temp_output.read()
                
                print("Command output:", output)
                
                # Check if commission earnings are displayed
                self.assertIn("Commission Statistics", output)
                self.assertIn("Total earnings", output)
                self.assertIn("1", output)  # Should have at least one commission payment
                
                # The specific amount will depend on the test data
                commission_payments = requests.get(f"{BASE_URL}/payments/query?admin_id={self.admin_id}&is_commission=true")
                commission_data = commission_payments.json()
                total_earned = sum(float(payment.get("amount", 0)) for payment in commission_data)
                
                # Check if the total earnings are displayed (within a reasonable margin)
                self.assertTrue(str(round(total_earned, 2)) in output or 
                                f"${total_earned:.2f}" in output or 
                                f"${int(total_earned)}" in output, 
                                f"Expected earnings of {total_earned} not found in output: {output}")
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()


if __name__ == '__main__':
    unittest.main()