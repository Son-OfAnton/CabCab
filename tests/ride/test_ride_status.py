"""Tests for ride status checking functionality in CabCab."""

import pytest
import json
import responses
from unittest.mock import patch, MagicMock
from app.services.ride_service import RideService, RideServiceError
from app.services.auth_service import AuthService, AuthError
from app.models.ride import RideStatus

# Constants for testing
TEST_BASE_URL = "http://localhost:3000"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzNDUtNjc4OTAtYWJjZGUtZWZnaGkiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTYwMDAwMDAwMH0.3GRZ-mDRrO7CYJhOBARgPCu7tVUFo9hFS7G4pVX2k1k"
TEST_USER_ID = "12345-67890-abcde-efghi"
TEST_RIDE_ID = "98765-43210-zyxwv-utsrq"
TEST_DRIVER_ID = "driver-789"
TEST_PICKUP_LOCATION_ID = "loc-123"
TEST_DROPOFF_LOCATION_ID = "loc-456"

@pytest.fixture
def mock_base_ride():
    """Basic ride fixture without location details."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_USER_ID,
        "pickup_location_id": TEST_PICKUP_LOCATION_ID,
        "dropoff_location_id": TEST_DROPOFF_LOCATION_ID,
        "status": RideStatus.REQUESTED.name,
        "estimated_fare": 25.50,
        "distance": 8.2,
        "duration": 18,
        "driver_id": None,
        "request_time": "2023-06-01T14:30:00",
        "start_time": None,
        "end_time": None,
        "actual_fare": None,
        "payment_id": None,
        "rating": None,
        "feedback": None
    }

@pytest.fixture
def mock_pickup_location():
    """Pickup location fixture."""
    return {
        "id": TEST_PICKUP_LOCATION_ID,
        "latitude": 40.7128,
        "longitude": -74.0060,
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "USA",
        "user_id": TEST_USER_ID
    }

@pytest.fixture
def mock_dropoff_location():
    """Dropoff location fixture."""
    return {
        "id": TEST_DROPOFF_LOCATION_ID,
        "latitude": 40.7581,
        "longitude": -73.9855,
        "address": "456 Broadway",
        "city": "New York",
        "state": "NY",
        "postal_code": "10013",
        "country": "USA",
        "user_id": TEST_USER_ID
    }

@pytest.fixture
def mock_driver_data():
    """Driver data fixture."""
    return {
        "id": TEST_DRIVER_ID,
        "email": "driver@example.com",
        "first_name": "John",
        "last_name": "Driver",
        "phone": "555-1234",
        "user_type": "driver",
        "license_number": "DL12345",
        "is_verified": True,
        "is_available": True,
        "rating": 4.8,
        "vehicle_id": "vehicle-123"
    }

@pytest.fixture
def mock_vehicle_data():
    """Vehicle data fixture."""
    return {
        "id": "vehicle-123",
        "make": "Toyota",
        "model": "Prius",
        "year": 2022,
        "color": "Silver",
        "license_plate": "ABC1234",
        "type": "ECONOMY",
        "capacity": 4,
        "driver_id": TEST_DRIVER_ID
    }

@pytest.fixture
def mock_requested_ride_with_locations(mock_base_ride, mock_pickup_location, mock_dropoff_location):
    """Full ride in REQUESTED status with location details."""
    ride = mock_base_ride.copy()
    ride["pickup_location"] = mock_pickup_location
    ride["dropoff_location"] = mock_dropoff_location
    return ride

@pytest.fixture
def mock_driver_assigned_ride_with_locations(mock_base_ride, mock_pickup_location, mock_dropoff_location):
    """Full ride in DRIVER_ASSIGNED status with location details."""
    ride = mock_base_ride.copy()
    ride["status"] = RideStatus.DRIVER_ASSIGNED.name
    ride["driver_id"] = TEST_DRIVER_ID
    ride["pickup_location"] = mock_pickup_location
    ride["dropoff_location"] = mock_dropoff_location
    return ride

@pytest.fixture
def mock_in_progress_ride_with_locations(mock_base_ride, mock_pickup_location, mock_dropoff_location):
    """Full ride in IN_PROGRESS status with location details."""
    ride = mock_base_ride.copy()
    ride["status"] = RideStatus.IN_PROGRESS.name
    ride["driver_id"] = TEST_DRIVER_ID
    ride["start_time"] = "2023-06-01T14:45:00"
    ride["pickup_location"] = mock_pickup_location
    ride["dropoff_location"] = mock_dropoff_location
    return ride

@pytest.fixture
def mock_completed_ride_with_locations(mock_base_ride, mock_pickup_location, mock_dropoff_location):
    """Full ride in COMPLETED status with location details."""
    ride = mock_base_ride.copy()
    ride["status"] = RideStatus.COMPLETED.name
    ride["driver_id"] = TEST_DRIVER_ID
    ride["start_time"] = "2023-06-01T14:45:00"
    ride["end_time"] = "2023-06-01T15:05:00"
    ride["actual_fare"] = 27.50
    ride["payment_id"] = "payment-123"
    ride["pickup_location"] = mock_pickup_location
    ride["dropoff_location"] = mock_dropoff_location
    return ride

class TestRideStatus:
    """Test class for ride status checking functionality."""
    
    @responses.activate
    def test_get_ride_by_id_requested_status(self, mock_base_ride, mock_pickup_location, mock_dropoff_location):
        """Test retrieving a ride in REQUESTED status."""
        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_base_ride,
            status=200
        )
        
        # Mock API responses for getting location details
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/locations/{TEST_PICKUP_LOCATION_ID}",
            json=mock_pickup_location,
            status=200
        )
        
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/locations/{TEST_DROPOFF_LOCATION_ID}",
            json=mock_dropoff_location,
            status=200
        )
        
        # Call the function being tested
        result = RideService.get_ride_by_id(TEST_RIDE_ID)
        
        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["status"] == RideStatus.REQUESTED.name
        assert result["driver_id"] is None
        
        # Verify location details are included
        assert "pickup_location" in result
        assert result["pickup_location"]["address"] == "123 Main St"
        assert result["pickup_location"]["city"] == "New York"
        
        assert "dropoff_location" in result
        assert result["dropoff_location"]["address"] == "456 Broadway"
        assert result["dropoff_location"]["city"] == "New York"
        
        # Verify all API calls were made
        assert len(responses.calls) == 3  # One GET for ride, two GETs for locations
    
    @responses.activate
    def test_get_ride_by_id_driver_assigned_status(self, mock_driver_assigned_ride_with_locations, 
                                               mock_driver_data, mock_vehicle_data):
        """Test retrieving a ride in DRIVER_ASSIGNED status with driver info."""
        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_driver_assigned_ride_with_locations,
            status=200
        )
        
        # Mock API response for getting driver details
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            json=mock_driver_data,
            status=200
        )
        
        # Mock API response for getting vehicle details
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/vehicles/{mock_driver_data['vehicle_id']}",
            json=mock_vehicle_data,
            status=200
        )
        
        # Call the function being tested
        result = RideService.get_ride_by_id(TEST_RIDE_ID, include_driver_details=True)
        
        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["status"] == RideStatus.DRIVER_ASSIGNED.name
        assert result["driver_id"] == TEST_DRIVER_ID
        
        # Verify location details are included
        assert "pickup_location" in result
        assert "dropoff_location" in result
        
        # Verify driver details are included
        assert "driver" in result
        assert result["driver"]["id"] == TEST_DRIVER_ID
        assert result["driver"]["first_name"] == "John"
        assert result["driver"]["last_name"] == "Driver"
        assert result["driver"]["phone"] == "555-1234"
        
        # Verify vehicle details are included
        assert "vehicle" in result
        assert result["vehicle"]["make"] == "Toyota"
        assert result["vehicle"]["model"] == "Prius"
        assert result["vehicle"]["color"] == "Silver"
        assert result["vehicle"]["license_plate"] == "ABC1234"
    
    @responses.activate
    def test_get_ride_by_id_driver_details_not_found(self, mock_driver_assigned_ride_with_locations):
        """Test handling when driver details can't be found."""
        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_driver_assigned_ride_with_locations,
            status=200
        )
        
        # Mock API response for getting driver details - 404 Not Found
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            json={"error": "Driver not found"},
            status=404
        )
        
        # Call the function being tested
        result = RideService.get_ride_by_id(TEST_RIDE_ID, include_driver_details=True)
        
        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["status"] == RideStatus.DRIVER_ASSIGNED.name
        assert result["driver_id"] == TEST_DRIVER_ID
        
        # Verify location details are included
        assert "pickup_location" in result
        assert "dropoff_location" in result
        
        # Driver details should not be included since API returned 404
        assert "driver" not in result
        assert "vehicle" not in result
    
    @responses.activate
    def test_get_ride_by_id_without_locations(self, mock_base_ride):
        """Test retrieving a ride without fetching location details."""
        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_base_ride,
            status=200
        )
        
        # Call the function being tested with include_locations=False
        result = RideService.get_ride_by_id(TEST_RIDE_ID, include_locations=False)
        
        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["status"] == RideStatus.REQUESTED.name
        
        # Verify location IDs are included but not location details
        assert "pickup_location_id" in result
        assert "dropoff_location_id" in result
        assert "pickup_location" not in result
        assert "dropoff_location" not in result
        
        # Verify only one API call was made
        assert len(responses.calls) == 1  # Only one GET for ride
    
    @responses.activate
    def test_get_ride_by_id_completed_status(self, mock_completed_ride_with_locations):
        """Test retrieving a completed ride with all details."""
        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_completed_ride_with_locations,
            status=200
        )
        
        # Call the function being tested
        result = RideService.get_ride_by_id(TEST_RIDE_ID)
        
        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["status"] == RideStatus.COMPLETED.name
        assert result["driver_id"] == TEST_DRIVER_ID
        assert result["start_time"] == "2023-06-01T14:45:00"
        assert result["end_time"] == "2023-06-01T15:05:00"
        assert result["actual_fare"] == 27.50
        assert result["payment_id"] == "payment-123"
        
        # Verify location details are included
        assert "pickup_location" in result
        assert "dropoff_location" in result
        
        # Verify all API calls were made
        assert len(responses.calls) == 1  # One GET for ride (locations already included)
    
    @responses.activate
    def test_get_ride_by_id_not_found(self):
        """Test error handling when ride is not found."""
        # Mock API response for non-existent ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json={"error": "Ride not found"},
            status=404
        )
        
        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.get_ride_by_id(TEST_RIDE_ID)
        
        # Verify the error message
        assert f"Ride with ID {TEST_RIDE_ID} not found" in str(excinfo.value)
    
    @responses.activate
    def test_get_ride_by_id_server_error(self):
        """Test handling of server errors."""
        # Mock API server error
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json={"error": "Internal server error"},
            status=500
        )
        
        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.get_ride_by_id(TEST_RIDE_ID)
        
        # Verify the error message
        assert "Failed to retrieve ride" in str(excinfo.value)