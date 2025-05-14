import unittest
import json
import uuid
import responses
import jwt
from datetime import datetime, timedelta

from app.services.vehicle_service import VehicleService, VehicleServiceError
from app.services.auth_service import AuthService, UserType, JWT_SECRET, JWT_ALGORITHM


class TestDriverVehicleList(unittest.TestCase):
    """Test suite for listing vehicles registered under a driver."""

    def setUp(self):
        """Set up test case with mock driver user and token."""
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
        
        # Start response mocking
        responses.start()

        # Create mock vehicles for the driver
        self.vehicles = [
            {
                "id": str(uuid.uuid4()),
                "make": "Toyota",
                "model": "Camry",
                "year": 2022,
                "color": "Blue",
                "license_plate": "ABC123",
                "vehicle_type": "COMFORT",
                "capacity": 4,
                "driver_id": self.driver_id,
                "created_at": datetime.now().isoformat(),
                "is_active": True
            },
            {
                "id": str(uuid.uuid4()),
                "make": "Honda",
                "model": "Civic",
                "year": 2021,
                "color": "Red",
                "license_plate": "XYZ789",
                "vehicle_type": "ECONOMY",
                "capacity": 4,
                "driver_id": self.driver_id,
                "created_at": datetime.now().isoformat(),
                "is_active": True
            },
            {
                "id": str(uuid.uuid4()),
                "make": "Ford",
                "model": "Explorer",
                "year": 2023,
                "color": "Black",
                "license_plate": "LMN456",
                "vehicle_type": "SUV",
                "capacity": 7,
                "driver_id": self.driver_id,
                "created_at": datetime.now().isoformat(),
                "is_active": False  # Inactive vehicle
            }
        ]

    def tearDown(self):
        """Clean up mocks after each test."""
        responses.stop()
        responses.reset()

    @responses.activate
    def test_get_driver_vehicles_success(self):
        """Test successfully listing all vehicles registered to a driver."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock the vehicles query endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/query?driver_id={self.driver_id}",
            json=self.vehicles,
            status=200
        )
        
        # Execute the get driver vehicles method
        result = VehicleService.get_driver_vehicles(self.token)
        
        # Assert the correct vehicles were returned
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["make"], "Toyota")
        self.assertEqual(result[0]["model"], "Camry")
        self.assertEqual(result[0]["license_plate"], "ABC123")
        
        self.assertEqual(result[1]["make"], "Honda")
        self.assertEqual(result[1]["model"], "Civic")
        self.assertEqual(result[1]["license_plate"], "XYZ789")
        
        self.assertEqual(result[2]["make"], "Ford")
        self.assertEqual(result[2]["model"], "Explorer")
        self.assertEqual(result[2]["vehicle_type"], "SUV")
        self.assertEqual(result[2]["capacity"], 7)
        self.assertFalse(result[2]["is_active"])
        
        # Verify all vehicles belong to the correct driver
        for vehicle in result:
            self.assertEqual(vehicle["driver_id"], self.driver_id)

    @responses.activate
    def test_get_driver_vehicles_no_vehicles(self):
        """Test listing vehicles when driver has no registered vehicles."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock the vehicles query endpoint - 404 response for no vehicles
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/query?driver_id={self.driver_id}",
            status=404
        )
        
        # Execute the get driver vehicles method
        result = VehicleService.get_driver_vehicles(self.token)
        
        # Assert an empty list is returned
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @responses.activate
    def test_get_driver_vehicles_empty_list(self):
        """Test listing vehicles when driver has no vehicles but endpoint returns empty list."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock the vehicles query endpoint - empty list response
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/query?driver_id={self.driver_id}",
            json=[],
            status=200
        )
        
        # Execute the get driver vehicles method
        result = VehicleService.get_driver_vehicles(self.token)
        
        # Assert an empty list is returned
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @responses.activate
    def test_get_driver_vehicles_invalid_user_type(self):
        """Test that non-driver users cannot list driver vehicles."""
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
        
        # Assert that getting vehicles fails with appropriate error
        with self.assertRaises(Exception) as context:
            VehicleService.get_driver_vehicles(passenger_token)
        
        self.assertIn("Access denied", str(context.exception))

    @responses.activate
    def test_get_driver_vehicles_server_error(self):
        """Test handling of server errors when listing vehicles."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock the vehicles query endpoint with server error
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/query?driver_id={self.driver_id}",
            status=500,
            json={"error": "Internal server error"}
        )
        
        # Assert that an error is raised with appropriate message
        with self.assertRaises(VehicleServiceError) as context:
            VehicleService.get_driver_vehicles(self.token)
        
        self.assertIn("Failed to retrieve vehicles", str(context.exception))

    @responses.activate
    def test_get_driver_vehicles_expired_token(self):
        """Test that expired tokens are rejected when listing vehicles."""
        # Create an expired token
        payload = {
            "user_id": self.driver_id,
            "user_type": UserType.DRIVER.value,
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Assert that the operation fails with appropriate error
        with self.assertRaises(Exception) as context:
            VehicleService.get_driver_vehicles(expired_token)
        
        self.assertIn("token", str(context.exception).lower())

    @responses.activate
    def test_get_driver_vehicles_filter_by_active_status(self):
        """Test that we can filter vehicles by active status."""
        # This test simulates what might be added as a feature later
        # to filter vehicles by active status. It would require modifying
        # the VehicleService.get_driver_vehicles method to accept an is_active parameter.
        
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock the vehicles query endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/query?driver_id={self.driver_id}",
            json=self.vehicles,
            status=200
        )
        
        # Execute the get driver vehicles method
        all_vehicles = VehicleService.get_driver_vehicles(self.token)
        
        # Manual filtering to simulate what the service might do
        active_vehicles = [v for v in all_vehicles if v["is_active"]]
        inactive_vehicles = [v for v in all_vehicles if not v["is_active"]]
        
        # Assert active vehicles filtering
        self.assertEqual(len(active_vehicles), 2)
        self.assertIn("Toyota", [v["make"] for v in active_vehicles])
        self.assertIn("Honda", [v["make"] for v in active_vehicles])
        self.assertNotIn("Ford", [v["make"] for v in active_vehicles])  # Ford vehicle is inactive
        
        # Assert inactive vehicles filtering
        self.assertEqual(len(inactive_vehicles), 1)
        self.assertEqual(inactive_vehicles[0]["make"], "Ford")
        self.assertEqual(inactive_vehicles[0]["model"], "Explorer")


if __name__ == '__main__':
    unittest.main()