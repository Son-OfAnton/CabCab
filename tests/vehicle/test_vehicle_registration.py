import unittest
import json
import uuid
import responses
import jwt
from datetime import datetime, timedelta

from app.services.vehicle_service import VehicleService, VehicleServiceError
from app.services.auth_service import AuthService, UserType, JWT_SECRET, JWT_ALGORITHM
from app.models.vehicle import VehicleType


class TestVehicleRegistration(unittest.TestCase):
    """Test suite for the vehicle registration functionality."""

    def setUp(self):
        """Set up test case with mock user and token."""
        # Create a mock driver user
        self.driver_id = str(uuid.uuid4())
        self.driver = {
            "id": self.driver_id,
            "email": "test.driver@example.com",
            "first_name": "Test",
            "last_name": "Driver",
            "phone": "555-123-4567",
            "user_type": UserType.DRIVER.value,
            "license_number": "DL12345678",
            "is_verified": True,
            "is_available": True,
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
        self.token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Mock vehicle data
        self.vehicle_data = {
            "make": "Toyota",
            "model": "Camry",
            "year": 2022,
            "color": "Blue",
            "license_plate": "ABC123",
            "vehicle_type": "COMFORT",
            "capacity": 4
        }
        
        # Start response mocking
        responses.start()

    def tearDown(self):
        """Clean up mocks after each test."""
        responses.stop()
        responses.reset()

    @responses.activate
    def test_register_vehicle_success(self):
        """Test successful vehicle registration for a driver."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock the check for existing license plate
        responses.add(
            responses.GET,
            "http://localhost:3000/vehicles/query?license_plate=ABC123",
            status=404  # Simulating no vehicle found
        )
        
        # Mock the vehicle creation
        vehicle_id = str(uuid.uuid4())
        new_vehicle = {
            "id": vehicle_id,
            "make": self.vehicle_data["make"],
            "model": self.vehicle_data["model"],
            "year": self.vehicle_data["year"],
            "color": self.vehicle_data["color"],
            "license_plate": self.vehicle_data["license_plate"],
            "vehicle_type": self.vehicle_data["vehicle_type"],
            "capacity": self.vehicle_data["capacity"],
            "driver_id": self.driver_id,
            "created_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        responses.add(
            responses.POST,
            "http://localhost:3000/vehicles",
            json=new_vehicle,
            status=201
        )
        
        # Mock the driver update endpoint (for setting primary vehicle)
        updated_driver = self.driver.copy()
        updated_driver["vehicle_id"] = vehicle_id
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.driver_id}",
            json=updated_driver,
            status=200
        )
        
        # Execute the vehicle registration
        vehicle = VehicleService.register_vehicle(
            self.token,
            self.vehicle_data["make"],
            self.vehicle_data["model"],
            self.vehicle_data["year"],
            self.vehicle_data["color"],
            self.vehicle_data["license_plate"],
            self.vehicle_data["vehicle_type"],
            self.vehicle_data["capacity"]
        )
        
        # Assert the returned vehicle has the correct data
        self.assertEqual(vehicle["make"], self.vehicle_data["make"])
        self.assertEqual(vehicle["model"], self.vehicle_data["model"])
        self.assertEqual(vehicle["year"], self.vehicle_data["year"])
        self.assertEqual(vehicle["color"], self.vehicle_data["color"])
        self.assertEqual(vehicle["license_plate"], self.vehicle_data["license_plate"])
        self.assertEqual(vehicle["vehicle_type"], self.vehicle_data["vehicle_type"])
        self.assertEqual(vehicle["capacity"], self.vehicle_data["capacity"])
        self.assertEqual(vehicle["driver_id"], self.driver_id)
        self.assertTrue(vehicle["is_active"])
        self.assertIn("id", vehicle)
        self.assertIn("created_at", vehicle)

    @responses.activate
    def test_register_vehicle_duplicate_license_plate(self):
        """Test vehicle registration fails with duplicate license plate."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock existing vehicle with same license plate
        existing_vehicle = {
            "id": str(uuid.uuid4()),
            "make": "Honda",
            "model": "Accord",
            "license_plate": "ABC123",
            "driver_id": str(uuid.uuid4())  # Different driver
        }
        
        responses.add(
            responses.GET,
            "http://localhost:3000/vehicles/query?license_plate=ABC123",
            json=[existing_vehicle],
            status=200
        )
        
        # Assert that registration fails with appropriate error
        with self.assertRaises(VehicleServiceError) as context:
            VehicleService.register_vehicle(
                self.token,
                self.vehicle_data["make"],
                self.vehicle_data["model"],
                self.vehicle_data["year"],
                self.vehicle_data["color"],
                self.vehicle_data["license_plate"],
                self.vehicle_data["vehicle_type"],
                self.vehicle_data["capacity"]
            )
        
        self.assertIn("already registered", str(context.exception))

    @responses.activate
    def test_register_vehicle_invalid_user_type(self):
        """Test vehicle registration fails for non-driver users."""
        # Create a passenger user
        passenger_id = str(uuid.uuid4())
        passenger = {
            "id": passenger_id,
            "email": "passenger@example.com",
            "user_type": UserType.PASSENGER.value
        }
        
        # Create a token for the passenger
        payload = {
            "user_id": passenger_id,
            "user_type": UserType.PASSENGER.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        passenger_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{passenger_id}",
            json=passenger,
            status=200
        )
        
        # Assert that registration fails with appropriate error
        with self.assertRaises(Exception) as context:
            VehicleService.register_vehicle(
                passenger_token,
                self.vehicle_data["make"],
                self.vehicle_data["model"],
                self.vehicle_data["year"],
                self.vehicle_data["color"],
                self.vehicle_data["license_plate"],
                self.vehicle_data["vehicle_type"],
                self.vehicle_data["capacity"]
            )
        
        self.assertIn("Access denied", str(context.exception))

    @responses.activate
    def test_register_vehicle_invalid_vehicle_type(self):
        """Test vehicle registration fails with invalid vehicle type."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock the check for existing license plate
        responses.add(
            responses.GET,
            "http://localhost:3000/vehicles/query?license_plate=ABC123",
            status=404  # Simulating no vehicle found
        )
        
        # Assert that registration fails with appropriate error
        with self.assertRaises(VehicleServiceError) as context:
            VehicleService.register_vehicle(
                self.token,
                self.vehicle_data["make"],
                self.vehicle_data["model"],
                self.vehicle_data["year"],
                self.vehicle_data["color"],
                self.vehicle_data["license_plate"],
                "INVALID_TYPE",  # Invalid vehicle type
                self.vehicle_data["capacity"]
            )
        
        self.assertIn("Invalid vehicle type", str(context.exception))

    @responses.activate
    def test_register_vehicle_expired_token(self):
        """Test vehicle registration fails with expired token."""
        # Create an expired token
        payload = {
            "user_id": self.driver_id,
            "user_type": UserType.DRIVER.value,
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Assert that registration fails with appropriate error
        with self.assertRaises(Exception) as context:
            VehicleService.register_vehicle(
                expired_token,
                self.vehicle_data["make"],
                self.vehicle_data["model"],
                self.vehicle_data["year"],
                self.vehicle_data["color"],
                self.vehicle_data["license_plate"],
                self.vehicle_data["vehicle_type"],
                self.vehicle_data["capacity"]
            )
        
        self.assertIn("token", str(context.exception).lower())


if __name__ == '__main__':
    unittest.main()