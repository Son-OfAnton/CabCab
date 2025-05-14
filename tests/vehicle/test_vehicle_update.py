import unittest
import json
import uuid
import responses
import jwt
from datetime import datetime, timedelta

from app.services.vehicle_service import VehicleService, VehicleServiceError
from app.services.auth_service import AuthService, UserType, JWT_SECRET, JWT_ALGORITHM
from app.models.vehicle import VehicleType


class TestUpdateVehicle(unittest.TestCase):
    """Test suite for the vehicle update functionality."""

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
        
        # Create a mock vehicle owned by the driver
        self.vehicle_id = str(uuid.uuid4())
        self.vehicle = {
            "id": self.vehicle_id,
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
        
        # Create another mock driver for permission tests
        self.other_driver_id = str(uuid.uuid4())
        self.other_driver = {
            "id": self.other_driver_id,
            "email": "other.driver@example.com",
            "user_type": UserType.DRIVER.value
        }
        
        # Create a vehicle owned by the other driver
        self.other_vehicle_id = str(uuid.uuid4())
        self.other_vehicle = {
            "id": self.other_vehicle_id,
            "make": "Honda",
            "model": "Civic",
            "year": 2021,
            "color": "Red",
            "license_plate": "XYZ789",
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
    def test_update_vehicle_success(self):
        """Test successfully updating vehicle information."""
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
            f"http://localhost:3000/vehicles/{self.vehicle_id}",
            json=self.vehicle,
            status=200
        )
        
        # Define updates to apply
        updates = {
            "color": "Silver",
            "year": 2023,
            "capacity": 5,
            "vehicle_type": "PREMIUM"
        }
        
        # Create expected updated vehicle
        updated_vehicle = self.vehicle.copy()
        for key, value in updates.items():
            updated_vehicle[key] = value
        
        # Mock update vehicle endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/vehicles/{self.vehicle_id}",
            json=updated_vehicle,
            status=200
        )
        
        # Execute the update
        result = VehicleService.update_vehicle(self.token, self.vehicle_id, updates)
        
        # Assert all updates were applied correctly
        self.assertEqual(result["id"], self.vehicle_id)
        self.assertEqual(result["color"], "Silver")
        self.assertEqual(result["year"], 2023)
        self.assertEqual(result["capacity"], 5)
        self.assertEqual(result["vehicle_type"], "PREMIUM")
        
        # Verify unchanged fields remain the same
        self.assertEqual(result["make"], self.vehicle["make"])
        self.assertEqual(result["model"], self.vehicle["model"])
        self.assertEqual(result["license_plate"], self.vehicle["license_plate"])
        self.assertEqual(result["driver_id"], self.driver_id)

    @responses.activate
    def test_update_vehicle_partial_update(self):
        """Test updating only a subset of vehicle fields."""
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
            f"http://localhost:3000/vehicles/{self.vehicle_id}",
            json=self.vehicle,
            status=200
        )
        
        # Define partial updates
        updates = {
            "color": "Black"
        }
        
        # Create expected updated vehicle
        updated_vehicle = self.vehicle.copy()
        updated_vehicle["color"] = "Black"
        
        # Mock update vehicle endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/vehicles/{self.vehicle_id}",
            json=updated_vehicle,
            status=200
        )
        
        # Execute the update
        result = VehicleService.update_vehicle(self.token, self.vehicle_id, updates)
        
        # Assert only the color was updated
        self.assertEqual(result["color"], "Black")
        
        # Verify all other fields remain the same
        self.assertEqual(result["make"], self.vehicle["make"])
        self.assertEqual(result["model"], self.vehicle["model"])
        self.assertEqual(result["year"], self.vehicle["year"])
        self.assertEqual(result["capacity"], self.vehicle["capacity"])
        self.assertEqual(result["vehicle_type"], self.vehicle["vehicle_type"])

    @responses.activate
    def test_update_vehicle_change_active_status(self):
        """Test switching a vehicle's active status."""
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
            f"http://localhost:3000/vehicles/{self.vehicle_id}",
            json=self.vehicle,
            status=200
        )
        
        # Define updates to apply
        updates = {
            "is_active": False
        }
        
        # Create expected updated vehicle
        updated_vehicle = self.vehicle.copy()
        updated_vehicle["is_active"] = False
        
        # Mock update vehicle endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/vehicles/{self.vehicle_id}",
            json=updated_vehicle,
            status=200
        )
        
        # Execute the update
        result = VehicleService.update_vehicle(self.token, self.vehicle_id, updates)
        
        # Assert active status was updated
        self.assertFalse(result["is_active"])
        
        # Verify other fields remain unchanged
        self.assertEqual(result["make"], self.vehicle["make"])
        self.assertEqual(result["model"], self.vehicle["model"])
        self.assertEqual(result["color"], self.vehicle["color"])

    @responses.activate
    def test_update_vehicle_not_found(self):
        """Test updating a vehicle that doesn't exist."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock get vehicle endpoint with 404 Not Found
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/{self.vehicle_id}",
            status=404
        )
        
        # Define updates to apply
        updates = {
            "color": "Silver",
        }
        
        # Assert appropriate error is raised
        with self.assertRaises(VehicleServiceError) as context:
            VehicleService.update_vehicle(self.token, self.vehicle_id, updates)
        
        self.assertIn("not found", str(context.exception).lower())

    @responses.activate
    def test_update_vehicle_unauthorized(self):
        """Test updating a vehicle that belongs to another driver."""
        # Mock the user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Mock get vehicle endpoint with other driver's vehicle
        responses.add(
            responses.GET,
            f"http://localhost:3000/vehicles/{self.other_vehicle_id}",
            json=self.other_vehicle,
            status=200
        )
        
        # Define updates to apply
        updates = {
            "color": "Silver",
        }
        
        # Assert appropriate error is raised
        with self.assertRaises(VehicleServiceError) as context:
            VehicleService.update_vehicle(self.token, self.other_vehicle_id, updates)
        
        self.assertIn("permission", str(context.exception).lower())

    @responses.activate
    def test_update_vehicle_invalid_vehicle_type(self):
        """Test updating vehicle type with an invalid type."""
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
            f"http://localhost:3000/vehicles/{self.vehicle_id}",
            json=self.vehicle,
            status=200
        )
        
        # Define updates with invalid vehicle type
        updates = {
            "vehicle_type": "INVALID_TYPE"
        }
        
        # Assert appropriate error is raised
        with self.assertRaises(VehicleServiceError) as context:
            VehicleService.update_vehicle(self.token, self.vehicle_id, updates)
        
        self.assertIn("invalid vehicle type", str(context.exception).lower())

    @responses.activate
    def test_update_vehicle_protected_fields(self):
        """Test attempting to update protected fields like id, driver_id, created_at."""
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
            f"http://localhost:3000/vehicles/{self.vehicle_id}",
            json=self.vehicle,
            status=200
        )
        
        # Define updates to apply including protected fields
        new_id = str(uuid.uuid4())
        new_driver_id = str(uuid.uuid4())
        new_created_at = (datetime.now() - timedelta(days=30)).isoformat()
        
        updates = {
            "color": "Silver",
            "id": new_id,
            "driver_id": new_driver_id,
            "created_at": new_created_at
        }
        
        # Create expected updated vehicle
        updated_vehicle = self.vehicle.copy()
        updated_vehicle["color"] = "Silver"
        # Protected fields should not be changed
        
        # Mock update vehicle endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/vehicles/{self.vehicle_id}",
            json=updated_vehicle,
            status=200
        )
        
        # Execute the update
        result = VehicleService.update_vehicle(self.token, self.vehicle_id, updates)
        
        # Assert color was updated
        self.assertEqual(result["color"], "Silver")
        
        # Verify protected fields remain unchanged
        self.assertEqual(result["id"], self.vehicle_id)
        self.assertEqual(result["driver_id"], self.driver_id)
        self.assertEqual(result["created_at"], self.vehicle["created_at"])

    @responses.activate
    def test_update_vehicle_expired_token(self):
        """Test updating a vehicle with an expired token."""
        # Create an expired token
        payload = {
            "user_id": self.driver_id,
            "user_type": UserType.DRIVER.value,
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Define updates to apply
        updates = {
            "color": "Silver",
        }
        
        # Assert appropriate error is raised
        with self.assertRaises(Exception) as context:
            VehicleService.update_vehicle(expired_token, self.vehicle_id, updates)
        
        self.assertIn("token", str(context.exception).lower())

    @responses.activate
    def test_update_vehicle_non_driver_user(self):
        """Test that non-driver users cannot update vehicles."""
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
        
        # Define updates to apply
        updates = {
            "color": "Silver",
        }
        
        # Assert appropriate error is raised
        with self.assertRaises(Exception) as context:
            VehicleService.update_vehicle(passenger_token, self.vehicle_id, updates)
        
        self.assertIn("access denied", str(context.exception).lower())


if __name__ == '__main__':
    unittest.main()