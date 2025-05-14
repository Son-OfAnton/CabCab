import unittest
import json
import uuid
import responses
import jwt
from datetime import datetime, timedelta

from app.services.vehicle_service import VehicleService, VehicleServiceError
from app.services.auth_service import AuthService, UserType, JWT_SECRET, JWT_ALGORITHM


class TestDeleteVehicle(unittest.TestCase):
    """Test suite for the vehicle deletion functionality."""

    def setUp(self):
        """Set up test case with mock driver user, token, and vehicle."""
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
            "updated_at": datetime.now().isoformat(),
            "vehicle_id": None  # Will be set for specific tests
        }

        # Generate a valid JWT token for the driver
        payload = {
            "user_id": self.driver_id,
            "user_type": UserType.DRIVER.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        self.token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Create multiple mock vehicles owned by the driver
        self.primary_vehicle_id = str(uuid.uuid4())
        self.primary_vehicle = {
            "id": self.primary_vehicle_id,
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
        }
        
        self.secondary_vehicle_id = str(uuid.uuid4())
        self.secondary_vehicle = {
            "id": self.secondary_vehicle_id,
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
        }
        
        # Create a mock vehicle owned by another driver
        self.other_driver_id = str(uuid.uuid4())
        self.other_vehicle_id = str(uuid.uuid4())
        self.other_vehicle = {
            "id": self.other_vehicle_id,
            "make": "Ford",
            "model": "Focus",
            "year": 2020,
            "color": "Gray",
            "license_plate": "OTH456",
            "vehicle_type": "ECONOMY",
            "capacity": 4,
            "driver_id": self.other_driver_id,
            "created_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        # Start response mocking
        responses.start()

    def tearDown(self):
        """Clean up mocks after each test."""
        responses.stop()
        responses.reset()

    @responses.activate
    def test_delete_vehicle_success(self):
        """Test successfully deleting a non-primary vehicle."""
        # Driver has multiple vehicles but the secondary vehicle is not set as primary
        self.driver["vehicle_id"] = self.primary_vehicle_id
        
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock get vehicle endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/{self.secondary_vehicle_id}",
            json=self.secondary_vehicle,
            status=200
        )
        
        # Mock delete vehicle endpoint
        responses.add(
            responses.DELETE,
            f"http://localhost:3000/vehicles/{self.secondary_vehicle_id}",
            json=self.secondary_vehicle,
            status=200
        )
        
        # Execute the delete
        result = VehicleService.delete_vehicle(self.token, self.secondary_vehicle_id)
        
        # Assert deletion was successful
        self.assertTrue(result)

    @responses.activate
    def test_delete_primary_vehicle_with_fallback(self):
        """Test deleting primary vehicle when driver has other vehicles."""
        # Set the primary vehicle
        self.driver["vehicle_id"] = self.primary_vehicle_id
        
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock get vehicle endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/{self.primary_vehicle_id}",
            json=self.primary_vehicle,
            status=200
        )
        
        # Mock get driver vehicles endpoint to return both vehicles
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/query?driver_id={self.driver_id}",
            json=[self.primary_vehicle, self.secondary_vehicle],
            status=200
        )
        
        # Mock update driver endpoint (to change primary vehicle)
        updated_driver = self.driver.copy()
        updated_driver["vehicle_id"] = self.secondary_vehicle_id
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.driver_id}",
            json=updated_driver,
            status=200
        )
        
        # Mock delete vehicle endpoint
        responses.add(
            responses.DELETE,
            f"http://localhost:3000/vehicles/{self.primary_vehicle_id}",
            json=self.primary_vehicle,
            status=200
        )
        
        # Execute the delete
        result = VehicleService.delete_vehicle(self.token, self.primary_vehicle_id)
        
        # Assert deletion was successful
        self.assertTrue(result)

    @responses.activate
    def test_delete_last_vehicle(self):
        """Test deleting the driver's only vehicle."""
        # Set the primary vehicle
        self.driver["vehicle_id"] = self.primary_vehicle_id
        
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock get vehicle endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/{self.primary_vehicle_id}",
            json=self.primary_vehicle,
            status=200
        )
        
        # Mock get driver vehicles endpoint to return only one vehicle
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/query?driver_id={self.driver_id}",
            json=[self.primary_vehicle],
            status=200
        )
        
        # Mock update driver endpoint (to set vehicle_id to null)
        updated_driver = self.driver.copy()
        updated_driver["vehicle_id"] = None
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.driver_id}",
            json=updated_driver,
            status=200
        )
        
        # Mock delete vehicle endpoint
        responses.add(
            responses.DELETE,
            f"http://localhost:3000/vehicles/{self.primary_vehicle_id}",
            json=self.primary_vehicle,
            status=200
        )
        
        # Execute the delete
        result = VehicleService.delete_vehicle(self.token, self.primary_vehicle_id)
        
        # Assert deletion was successful
        self.assertTrue(result)

    @responses.activate
    def test_delete_vehicle_not_found(self):
        """Test deleting a vehicle that doesn't exist."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Non-existent vehicle ID
        non_existent_id = str(uuid.uuid4())
        
        # Mock get vehicle endpoint with 404 Not Found
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/{non_existent_id}",
            status=404,
            json={"error": "Vehicle not found"}
        )
        
        # Assert appropriate error is raised
        with self.assertRaises(VehicleServiceError) as context:
            VehicleService.delete_vehicle(self.token, non_existent_id)
        
        self.assertIn("not found", str(context.exception).lower())

    @responses.activate
    def test_delete_other_drivers_vehicle(self):
        """Test deleting a vehicle owned by another driver."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock get vehicle endpoint to return the other driver's vehicle
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/{self.other_vehicle_id}",
            json=self.other_vehicle,
            status=200
        )
        
        # Assert appropriate error is raised
        with self.assertRaises(VehicleServiceError) as context:
            VehicleService.delete_vehicle(self.token, self.other_vehicle_id)
        
        self.assertIn("permission", str(context.exception).lower())

    @responses.activate
    def test_delete_vehicle_expired_token(self):
        """Test deleting a vehicle with an expired token."""
        # Create an expired token
        payload = {
            "user_id": self.driver_id,
            "user_type": UserType.DRIVER.value,
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Assert appropriate error is raised
        with self.assertRaises(Exception) as context:
            VehicleService.delete_vehicle(expired_token, self.primary_vehicle_id)
        
        self.assertIn("token", str(context.exception).lower())

    @responses.activate
    def test_delete_vehicle_server_error(self):
        """Test handling server errors during deletion."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock get vehicle endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/{self.secondary_vehicle_id}",
            json=self.secondary_vehicle,
            status=200
        )
        
        # Mock delete vehicle endpoint with server error
        responses.add(
            responses.DELETE,
            f"http://localhost:3000/vehicles/{self.secondary_vehicle_id}",
            status=500,
            json={"error": "Internal server error"}
        )
        
        # Assert appropriate error is raised
        with self.assertRaises(VehicleServiceError) as context:
            VehicleService.delete_vehicle(self.token, self.secondary_vehicle_id)
        
        self.assertIn("failed to delete", str(context.exception).lower())

    @responses.activate
    def test_delete_vehicle_non_driver_user(self):
        """Test that non-driver users cannot delete vehicles."""
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
        
        # Assert appropriate error is raised
        with self.assertRaises(Exception) as context:
            VehicleService.delete_vehicle(passenger_token, self.primary_vehicle_id)
        
        self.assertIn("access denied", str(context.exception).lower())

    @responses.activate
    def test_delete_vehicle_driver_update_fails(self):
        """Test handling errors when updating driver after vehicle deletion."""
        # Set the primary vehicle
        self.driver["vehicle_id"] = self.primary_vehicle_id
        
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock get vehicle endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/{self.primary_vehicle_id}",
            json=self.primary_vehicle,
            status=200
        )
        
        # Mock get driver vehicles endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/query?driver_id={self.driver_id}",
            json=[self.primary_vehicle, self.secondary_vehicle],
            status=200
        )
        
        # Mock update driver endpoint with failure
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.driver_id}",
            status=500,
            json={"error": "Failed to update driver"}
        )
        
        # Assert appropriate error is raised
        with self.assertRaises(VehicleServiceError) as context:
            VehicleService.delete_vehicle(self.token, self.primary_vehicle_id)
        
        self.assertIn("failed", str(context.exception).lower())


if __name__ == '__main__':
    unittest.main()