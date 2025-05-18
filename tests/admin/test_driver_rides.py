"""
Test for admin driver-rides command.

This test:
1. Sets up test data (admin, passenger, driver, vehicles, locations, rides)
2. Tests the admin driver-rides command with various options
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
from app.services.ride_service import RideService

# Constants for our test
BASE_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Admin123!"
PASSENGER_EMAIL = "passenger@test.com"
PASSENGER_PASSWORD = "Pass123!"
DRIVER_EMAIL = "driver@test.com"
DRIVER_PASSWORD = "Driver123!"


class TestAdminDriverRidesCommand(unittest.TestCase):
    """Test the 'cabcab admin driver-rides' command."""

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
                "payments": []
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
        """Create test users, drivers, vehicles, and rides."""
        print("Creating test data...")
        
        # Create admin user
        admin_id = str(uuid.uuid4())
        admin = {
            "id": admin_id,
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
        passenger_id = str(uuid.uuid4())
        passenger = {
            "id": passenger_id,
            "email": PASSENGER_EMAIL,
            "password": "hashed_password",  # In real app, this would be hashed
            "first_name": "Test",
            "last_name": "Passenger",
            "phone": "555-PASS",
            "user_type": UserType.PASSENGER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True,
            "payment_methods": ["credit_card_1"]
        }
        
        # Create driver user
        driver_id = str(uuid.uuid4())
        driver = {
            "id": driver_id,
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
        
        # Create a vehicle for the driver
        vehicle_id = str(uuid.uuid4())
        vehicle = {
            "id": vehicle_id,
            "driver_id": driver_id,
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
        
        # Create locations
        pickup_location_id_1 = str(uuid.uuid4())
        pickup_location_1 = {
            "id": pickup_location_id_1,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country": "USA",
            "user_id": passenger_id
        }
        
        dropoff_location_id_1 = str(uuid.uuid4())
        dropoff_location_1 = {
            "id": dropoff_location_id_1,
            "latitude": 40.7306,
            "longitude": -73.9352,
            "address": "456 Broadway",
            "city": "New York",
            "state": "NY",
            "postal_code": "10002",
            "country": "USA",
            "user_id": passenger_id
        }
        
        pickup_location_id_2 = str(uuid.uuid4())
        pickup_location_2 = {
            "id": pickup_location_id_2,
            "latitude": 40.7306,
            "longitude": -73.9352,
            "address": "789 Park Ave",
            "city": "New York",
            "state": "NY",
            "postal_code": "10003",
            "country": "USA",
            "user_id": passenger_id
        }
        
        dropoff_location_id_2 = str(uuid.uuid4())
        dropoff_location_2 = {
            "id": dropoff_location_id_2,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "address": "321 5th Ave",
            "city": "New York",
            "state": "NY",
            "postal_code": "10004",
            "country": "USA",
            "user_id": passenger_id
        }
        
        # Create rides
        # Ride 1: Completed ride with driver, rating, and payment
        ride_id_1 = str(uuid.uuid4())
        payment_id_1 = str(uuid.uuid4())
        
        ride_1 = {
            "id": ride_id_1,
            "user_id": passenger_id,
            "driver_id": driver_id,
            "pickup_location_id": pickup_location_id_1,
            "dropoff_location_id": dropoff_location_id_1,
            "request_time": (datetime.now() - timedelta(days=2)).isoformat(),
            "start_time": (datetime.now() - timedelta(days=2, hours=23)).isoformat(),
            "end_time": (datetime.now() - timedelta(days=2, hours=23, minutes=30)).isoformat(),
            "status": "COMPLETED",
            "estimated_fare": 25.50,
            "actual_fare": 27.75,
            "distance": 5.2,
            "duration": 30,
            "payment_id": payment_id_1,
            "rating": 4,
            "feedback": "Good ride, driver was polite."
        }
        
        payment_1 = {
            "id": payment_id_1,
            "user_id": passenger_id,
            "ride_id": ride_id_1,
            "amount": 27.75,
            "payment_method": "CREDIT_CARD",
            "status": "COMPLETED",
            "timestamp": (datetime.now() - timedelta(days=2, hours=23, minutes=30)).isoformat()
        }
        
        # Ride 2: In-progress ride with driver
        ride_id_2 = str(uuid.uuid4())
        
        ride_2 = {
            "id": ride_id_2,
            "user_id": passenger_id,
            "driver_id": driver_id,
            "pickup_location_id": pickup_location_id_2,
            "dropoff_location_id": dropoff_location_id_2,
            "request_time": (datetime.now() - timedelta(hours=1)).isoformat(),
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "status": "IN_PROGRESS",
            "estimated_fare": 18.75,
            "actual_fare": None,
            "distance": 3.8,
            "duration": 22,
            "payment_id": None,
            "rating": None,
            "feedback": None
        }
        
        # Save test data to database
        cls.post_data("users", admin)
        cls.post_data("users", passenger)
        cls.post_data("users", driver)
        cls.post_data("vehicles", vehicle)
        cls.post_data("locations", pickup_location_1)
        cls.post_data("locations", dropoff_location_1)
        cls.post_data("locations", pickup_location_2)
        cls.post_data("locations", dropoff_location_2)
        cls.post_data("rides", ride_1)
        cls.post_data("rides", ride_2)
        cls.post_data("payments", payment_1)
        
        # Store IDs for later use
        cls.admin_id = admin_id
        cls.passenger_id = passenger_id
        cls.driver_id = driver_id
        cls.vehicle_id = vehicle_id
        cls.ride_id_1 = ride_id_1
        cls.ride_id_2 = ride_id_2
        
        print("Test data created")
    
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
                for collection in ["payments", "rides", "locations", "vehicles", "drivers", "users"]:
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
    
    def login_as_admin(self):
        """Log in as admin and save token to config file."""
        # Mock the AuthService.login method to return a token without needing a real login
        with patch('app.services.auth_service.AuthService.login') as mock_login:
            admin_data = {
                "id": self.admin_id,
                "email": ADMIN_EMAIL,
                "first_name": "Admin",
                "last_name": "User",
                "user_type": UserType.ADMIN.value
            }
            
            # Create a token that will pass verification
            # In a real test, you might use the actual JWT generation
            mock_token = "fake_admin_token"
            
            mock_login.return_value = {
                "token": mock_token,
                "user": admin_data
            }
            
            # Save token to config file
            with open(os.path.join(self.config_dir, "config.json"), 'w') as f:
                json.dump({"token": mock_token}, f)
            
            # Mock token verification to return the admin user
            with patch('app.services.auth_service.AuthService.verify_token') as mock_verify:
                mock_verify.return_value = admin_data
                
                # Mock the require_user_type method to allow admin
                with patch('app.services.auth_service.AuthService.require_user_type') as mock_require:
                    mock_require.return_value = admin_data
                    
                    # Return the patchers for later cleanup
                    return mock_login, mock_verify, mock_require
    
    def test_driver_rides_command_table_format(self):
        """Test the 'cabcab admin driver-rides' command with table output format."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commands import driver_rides; driver_rides('{DRIVER_EMAIL}', None, 'table')"
                ]
                
                # Execute command and capture output
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
                self.assertIn(f"Rides for driver", output)
                self.assertIn(f"Total rides found: 2", output)
                self.assertIn("COMPLETED", output)
                self.assertIn("IN_PROGRESS", output)
                self.assertIn("123 Main St", output)
                self.assertIn("789 Park Ave", output)
                self.assertIn("Test Passenger", output) # Passenger name
                self.assertIn("4/5", output)  # Rating for the completed ride
                
                print("Test output:", output)
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_driver_rides_command_detailed_format(self):
        """Test the 'cabcab admin driver-rides' command with detailed output format."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commands import driver_rides; driver_rides('{DRIVER_EMAIL}', None, 'detailed')"
                ]
                
                # Execute command and capture output
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
                
                # Verify output contains detailed information
                self.assertIn(f"Rides for driver", output)
                self.assertIn(f"Total rides found: 2", output)
                self.assertIn("Ride 1/2", output)
                self.assertIn("Ride 2/2", output)
                self.assertIn("Status: COMPLETED", output)
                self.assertIn("Status: IN_PROGRESS", output)
                self.assertIn("Passenger Information:", output)
                self.assertIn("Test Passenger", output)
                self.assertIn("Vehicle Information:", output)
                self.assertIn("Toyota Camry", output)
                self.assertIn("Pickup Location:", output)
                self.assertIn("Dropoff Location:", output)
                self.assertIn("Address: 123 Main St", output)
                self.assertIn("Rating: 4", output)
                self.assertIn("Feedback:", output)
                self.assertIn("Good ride, driver was polite", output)
                self.assertIn("Driver Earnings:", output)
                
                print("Test output:", output)
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_driver_rides_command_with_status_filter(self):
        """Test the 'cabcab admin driver-rides' command with status filter."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commands import driver_rides; driver_rides('{DRIVER_EMAIL}', 'COMPLETED', 'table')"
                ]
                
                # Execute command and capture output
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
                
                # Verify output contains only COMPLETED rides
                self.assertIn(f"Rides for driver", output)
                self.assertIn(f"Filtered by status: COMPLETED", output)
                self.assertIn("COMPLETED", output)
                self.assertNotIn("IN_PROGRESS", output)
                self.assertIn("123 Main St", output)
                self.assertNotIn("789 Park Ave", output)
                
                print("Test output:", output)
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_driver_rides_command_with_invalid_email(self):
        """Test the 'cabcab admin driver-rides' command with an invalid email."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commands import driver_rides; driver_rides('invalid@test.com', None, 'table')"
                ]
                
                # Execute command and capture output
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
                
                # Verify error message is shown
                self.assertIn("Error:", output)
                self.assertIn("not found", output)
                
                print("Test output:", output)
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_driver_rides_command_with_passenger_email(self):
        """Test the 'cabcab admin driver-rides' command with a passenger email (not a driver)."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Create a temporary file to capture command output
            with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                # Prepare command to run
                command = [
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commands import driver_rides; driver_rides('{PASSENGER_EMAIL}', None, 'table')"
                ]
                
                # Execute command and capture output
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
                
                # Verify error message is shown
                self.assertIn("Error:", output)
                self.assertIn("not a driver", output)
                
                print("Test output:", output)
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()


if __name__ == '__main__':
    # Run the tests
    unittest.main()