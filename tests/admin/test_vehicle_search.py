"""
Test for admin search-vehicle command.

This test suite verifies the functionality of the admin search-vehicle command,
which allows admins to find vehicles by their license plates.
"""

import os
import sys
import json
import unittest
import subprocess
import tempfile
import shutil
import requests
import uuid
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add the project root to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.models.user import UserType
from app.services.auth_service import AuthService
from app.services.vehicle_service import VehicleService

# Constants for our test
BASE_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Admin123!"
DRIVER_EMAIL = "driver@test.com"
DRIVER_PASSWORD = "Driver123!"


class TestAdminVehicleSearchCommand(unittest.TestCase):
    """Test the 'cabcab admin search-vehicle' command."""

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
        
        # Use subprocess to run the server
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
        """Create test users, drivers, and vehicles."""
        print("Creating test data...")
        
        # Create admin user
        admin_id = str(uuid.uuid4())
        admin = {
            "id": admin_id,
            "email": ADMIN_EMAIL,
            "password": "hashed_password",  # In a real app, this would be hashed
            "first_name": "Admin",
            "last_name": "User",
            "phone": "555-ADMIN",
            "user_type": UserType.ADMIN.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        # Create driver user
        driver_id = str(uuid.uuid4())
        driver = {
            "id": driver_id,
            "email": DRIVER_EMAIL,
            "password": "hashed_password",  # In a real app, this would be hashed
            "first_name": "Test",
            "last_name": "Driver",
            "phone": "555-DRIVER",
            "user_type": UserType.DRIVER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True,
            "is_verified": True,
            "license_number": "DL12345678"
        }
        
        # Create a second driver (unverified)
        driver2_id = str(uuid.uuid4())
        driver2 = {
            "id": driver2_id,
            "email": "driver2@test.com",
            "password": "hashed_password",
            "first_name": "Second",
            "last_name": "Driver",
            "phone": "555-DRIVER2",
            "user_type": UserType.DRIVER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True,
            "is_verified": False,
            "license_number": "DL87654321"
        }
        
        # Create vehicles
        vehicle_id = str(uuid.uuid4())
        vehicle = {
            "id": vehicle_id,
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "color": "Blue",
            "license_plate": "ABC-123",
            "vehicle_type": "COMFORT",
            "capacity": 4,
            "driver_id": driver_id,
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "is_active": True
        }
        
        vehicle2_id = str(uuid.uuid4())
        vehicle2 = {
            "id": vehicle2_id,
            "make": "Honda",
            "model": "Civic",
            "year": 2021,
            "color": "Red",
            "license_plate": "XYZ-789",
            "vehicle_type": "ECONOMY",
            "capacity": 4,
            "driver_id": driver2_id,
            "created_at": (datetime.now() - timedelta(days=15)).isoformat(),
            "is_active": True
        }
        
        # Create a vehicle with similar license plate
        vehicle3_id = str(uuid.uuid4())
        vehicle3 = {
            "id": vehicle3_id,
            "make": "BMW",
            "model": "X5",
            "year": 2022,
            "color": "Black",
            "license_plate": "ABC-456",
            "vehicle_type": "PREMIUM",
            "capacity": 5,
            "driver_id": driver_id,
            "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
            "is_active": True
        }
        
        # Save test data to database
        cls.post_data("users", admin)
        cls.post_data("users", driver)
        cls.post_data("users", driver2)
        cls.post_data("vehicles", vehicle)
        cls.post_data("vehicles", vehicle2)
        cls.post_data("vehicles", vehicle3)
        
        # Store IDs for later use
        cls.admin_id = admin_id
        cls.driver_id = driver_id
        cls.driver2_id = driver2_id
        cls.vehicle_id = vehicle_id
        cls.vehicle2_id = vehicle2_id
        cls.vehicle3_id = vehicle3_id
        
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
                for collection in ["payments", "rides", "locations", "vehicles", "users"]:
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
        # Mock the AuthService.login method to return a token
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
    
    def test_search_vehicle_exact_match(self):
        """Test searching for a vehicle with exact license plate match."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Mock the find_vehicle_by_license_plate method
            with patch('app.services.vehicle_service.VehicleService.find_vehicle_by_license_plate') as mock_find:
                # Create a vehicle result
                vehicle_result = {
                    'vehicles': [
                        {
                            'id': self.vehicle_id,
                            'make': 'Toyota',
                            'model': 'Camry',
                            'year': 2020,
                            'color': 'Blue',
                            'license_plate': 'ABC-123',
                            'vehicle_type': 'COMFORT',
                            'capacity': 4,
                            'driver_id': self.driver_id,
                            'created_at': (datetime.now() - timedelta(days=30)).isoformat(),
                            'is_active': True,
                            'driver': {
                                'id': self.driver_id,
                                'name': 'Test Driver',
                                'email': DRIVER_EMAIL,
                                'phone': '555-DRIVER',
                                'is_verified': True,
                                'is_active': True
                            }
                        }
                    ],
                    'count': 1
                }
                
                mock_find.return_value = vehicle_result
                
                # Create a temporary file to capture command output
                with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                    # Prepare command to run
                    command = [
                        "python", "-c", 
                        "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commands import search_vehicle; search_vehicle('ABC-123', 'table')"
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
                    
                    # Verify the command output
                    self.assertIn("Found 1 vehicle with license plate", output)
                    self.assertIn("ABC-123", output)
                    self.assertIn("Toyota", output)
                    self.assertIn("Camry", output)
                    self.assertIn("COMFORT", output)
                    self.assertIn("Test Driver", output)
                    self.assertIn("Helpful commands", output)
                    
                    # Verify the mock was called with correct arguments
                    mock_find.assert_called_once()
                    call_args = mock_find.call_args[0]
                    self.assertEqual(call_args[1], "ABC-123")
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_search_vehicle_multiple_matches(self):
        """Test searching for vehicles with similar license plates (multiple matches)."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Mock the find_vehicle_by_license_plate method
            with patch('app.services.vehicle_service.VehicleService.find_vehicle_by_license_plate') as mock_find:
                # Create a result with multiple vehicles
                vehicle_result = {
                    'vehicles': [
                        {
                            'id': self.vehicle_id,
                            'make': 'Toyota',
                            'model': 'Camry',
                            'year': 2020,
                            'color': 'Blue',
                            'license_plate': 'ABC-123',
                            'vehicle_type': 'COMFORT',
                            'capacity': 4,
                            'driver_id': self.driver_id,
                            'created_at': (datetime.now() - timedelta(days=30)).isoformat(),
                            'is_active': True,
                            'driver': {
                                'id': self.driver_id,
                                'name': 'Test Driver',
                                'email': DRIVER_EMAIL,
                                'phone': '555-DRIVER',
                                'is_verified': True,
                                'is_active': True
                            }
                        },
                        {
                            'id': self.vehicle3_id,
                            'make': 'BMW',
                            'model': 'X5',
                            'year': 2022,
                            'color': 'Black',
                            'license_plate': 'ABC-456',
                            'vehicle_type': 'PREMIUM',
                            'capacity': 5,
                            'driver_id': self.driver_id,
                            'created_at': (datetime.now() - timedelta(days=10)).isoformat(),
                            'is_active': True,
                            'driver': {
                                'id': self.driver_id,
                                'name': 'Test Driver',
                                'email': DRIVER_EMAIL,
                                'phone': '555-DRIVER',
                                'is_verified': True,
                                'is_active': True
                            }
                        }
                    ],
                    'count': 2
                }
                
                mock_find.return_value = vehicle_result
                
                # Create a temporary file to capture command output
                with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                    # Prepare command to run
                    command = [
                        "python", "-c", 
                        "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commands import search_vehicle; search_vehicle('ABC', 'table')"
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
                    
                    # Verify the command output
                    self.assertIn("Found 2 vehicles with license plate", output)
                    self.assertIn("ABC-123", output)
                    self.assertIn("ABC-456", output)
                    self.assertIn("Toyota", output)
                    self.assertIn("BMW", output)
                    self.assertIn("X5", output)
                    
                    # Verify the mock was called with correct arguments
                    mock_find.assert_called_once()
                    call_args = mock_find.call_args[0]
                    self.assertEqual(call_args[1], "ABC")
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_search_vehicle_detailed_format(self):
        """Test searching for a vehicle with detailed output format."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Mock the find_vehicle_by_license_plate method
            with patch('app.services.vehicle_service.VehicleService.find_vehicle_by_license_plate') as mock_find:
                # Create a vehicle result
                vehicle_result = {
                    'vehicles': [
                        {
                            'id': self.vehicle2_id,
                            'make': 'Honda',
                            'model': 'Civic',
                            'year': 2021,
                            'color': 'Red',
                            'license_plate': 'XYZ-789',
                            'vehicle_type': 'ECONOMY',
                            'capacity': 4,
                            'driver_id': self.driver2_id,
                            'created_at': (datetime.now() - timedelta(days=15)).isoformat(),
                            'is_active': True,
                            'driver': {
                                'id': self.driver2_id,
                                'name': 'Second Driver',
                                'email': 'driver2@test.com',
                                'phone': '555-DRIVER2',
                                'is_verified': False,
                                'is_active': True
                            }
                        }
                    ],
                    'count': 1
                }
                
                mock_find.return_value = vehicle_result
                
                # Create a temporary file to capture command output
                with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                    # Prepare command to run
                    command = [
                        "python", "-c", 
                        "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commands import search_vehicle; search_vehicle('XYZ-789', 'detailed')"
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
                    
                    # Verify the detailed output contains all the expected information
                    self.assertIn("--- Vehicle 1/1 ---", output)
                    self.assertIn("ID:", output)
                    self.assertIn("License Plate: XYZ-789", output)
                    self.assertIn("Make: Honda", output)
                    self.assertIn("Model: Civic", output)
                    self.assertIn("Year: 2021", output)
                    self.assertIn("Color: Red", output)
                    self.assertIn("Type: ECONOMY", output)
                    self.assertIn("Capacity: 4 passengers", output)
                    self.assertIn("Status: Active", output)
                    
                    self.assertIn("Driver Information:", output)
                    self.assertIn("Name: Second Driver", output)
                    self.assertIn("Email: driver2@test.com", output)
                    self.assertIn("Phone: 555-DRIVER2", output)
                    self.assertIn("Verification: Not Verified", output)
                    
                    # Verify the mock was called with correct arguments
                    mock_find.assert_called_once()
                    call_args = mock_find.call_args[0]
                    self.assertEqual(call_args[1], "XYZ-789")
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()
    
    def test_search_vehicle_not_found(self):
        """Test searching for a non-existent vehicle."""
        # Login as admin
        mock_login, mock_verify, mock_require = self.login_as_admin()
        
        try:
            # Mock the find_vehicle_by_license_plate method to raise an exception
            with patch('app.services.vehicle_service.VehicleService.find_vehicle_by_license_plate') as mock_find:
                # Make the mock raise a VehicleServiceError
                from app.services.vehicle_service import VehicleServiceError
                mock_find.side_effect = VehicleServiceError("No vehicle found with license plate similar to 'NOT-FOUND'")
                
                # Create a temporary file to capture command output
                with tempfile.NamedTemporaryFile(mode='w+') as temp_output:
                    # Prepare command to run
                    command = [
                        "python", "-c", 
                        "import sys; sys.path.insert(0, '.'); from app.cli_module.commands.admin_commands import search_vehicle; search_vehicle('NOT-FOUND', 'table')"
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
                    
                    # Verify the error message
                    self.assertIn("Error:", output)
                    self.assertIn("No vehicle found with license plate", output)
                    
                    # Verify the mock was called with correct arguments
                    mock_find.assert_called_once()
                    call_args = mock_find.call_args[0]
                    self.assertEqual(call_args[1], "NOT-FOUND")
        finally:
            # Stop all mocks
            mock_login.stop()
            mock_verify.stop()
            mock_require.stop()


if __name__ == '__main__':
    unittest.main()