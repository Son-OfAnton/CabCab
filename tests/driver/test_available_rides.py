"""Tests for the driver available rides viewing feature in CabCab."""

import pytest
import json
import responses
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.services.ride_service import RideService, RideServiceError
from app.services.auth_service import AuthService, AuthError, UserType
from app.models.ride import RideStatus

# Constants for testing
TEST_BASE_URL = "http://localhost:3000"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZHJpdmVyLTEyMzQ1IiwidXNlcl90eXBlIjoiZHJpdmVyIiwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjE2MDAwMDAwMDB9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
TEST_DRIVER_ID = "driver-12345"


@pytest.fixture
def mock_driver_data():
    """Fixture for sample verified and available driver data."""
    return {
        "id": TEST_DRIVER_ID,
        "email": "driver@example.com",
        "first_name": "Test",
        "last_name": "Driver",
        "phone": "1234567890",
        "user_type": "driver",
        "license_number": "DL123456",
        "is_verified": True,  # Driver is verified
        "is_available": True,  # Driver is available
        "rating": 4.8,
        "rating_count": 25,
        "vehicle_id": "vehicle-789",
        "created_at": "2023-01-01T12:00:00",
        "updated_at": "2023-01-01T12:00:00"
    }


@pytest.fixture
def mock_unavailable_driver_data():
    """Fixture for a driver who is not available."""
    return {
        "id": TEST_DRIVER_ID,
        "email": "driver@example.com",
        "first_name": "Test",
        "last_name": "Driver",
        "phone": "1234567890",
        "user_type": "driver",
        "license_number": "DL123456",
        "is_verified": True,
        "is_available": False,  # Driver is not available
        "rating": 4.8,
        "rating_count": 25,
        "vehicle_id": "vehicle-789",
        "created_at": "2023-01-01T12:00:00",
        "updated_at": "2023-01-01T12:00:00"
    }


@pytest.fixture
def mock_unverified_driver_data():
    """Fixture for an unverified driver."""
    return {
        "id": TEST_DRIVER_ID,
        "email": "driver@example.com",
        "first_name": "Test",
        "last_name": "Driver",
        "phone": "1234567890",
        "user_type": "driver",
        "license_number": "DL123456",
        "is_verified": False,  # Driver is not verified
        "is_available": True,
        "rating": None,
        "rating_count": 0,
        "vehicle_id": "vehicle-789",
        "created_at": "2023-01-01T12:00:00",
        "updated_at": "2023-01-01T12:00:00"
    }


@pytest.fixture
def mock_ride_requests():
    """Fixture for a list of available ride requests."""
    now = datetime.now()
    
    return [
        {
            "id": "ride-001",
            "user_id": "user-111",
            "pickup_location_id": "loc-aaa",
            "dropoff_location_id": "loc-bbb",
            "status": RideStatus.REQUESTED.name,
            "estimated_fare": 25.50,
            "distance": 8.2,
            "duration": 18,
            "driver_id": None,
            "request_time": (now - timedelta(minutes=15)).isoformat(),
            "start_time": None,
            "end_time": None,
            "actual_fare": None,
            "payment_id": None,
            "rating": None,
            "feedback": None
        },
        {
            "id": "ride-002",
            "user_id": "user-222",
            "pickup_location_id": "loc-ccc",
            "dropoff_location_id": "loc-ddd",
            "status": RideStatus.REQUESTED.name,
            "estimated_fare": 15.75,
            "distance": 4.5,
            "duration": 12,
            "driver_id": None,
            "request_time": (now - timedelta(minutes=10)).isoformat(),
            "start_time": None,
            "end_time": None,
            "actual_fare": None,
            "payment_id": None,
            "rating": None,
            "feedback": None
        },
        {
            "id": "ride-003",
            "user_id": "user-333",
            "pickup_location_id": "loc-eee",
            "dropoff_location_id": "loc-fff",
            "status": RideStatus.REQUESTED.name,
            "estimated_fare": 35.25,
            "distance": 12.3,
            "duration": 28,
            "driver_id": None,
            "request_time": (now - timedelta(minutes=5)).isoformat(),
            "start_time": None,
            "end_time": None,
            "actual_fare": None,
            "payment_id": None,
            "rating": None,
            "feedback": None
        }
    ]


@pytest.fixture
def mock_pickup_location_for_ride1():
    """Pickup location for ride-001."""
    return {
        "id": "loc-aaa",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "USA",
        "user_id": "user-111"
    }


@pytest.fixture
def mock_dropoff_location_for_ride1():
    """Dropoff location for ride-001."""
    return {
        "id": "loc-bbb",
        "latitude": 40.7581,
        "longitude": -73.9855,
        "address": "456 Broadway",
        "city": "New York",
        "state": "NY",
        "postal_code": "10012",
        "country": "USA",
        "user_id": "user-111"
    }


@pytest.fixture
def mock_ride_with_locations(mock_ride_requests, mock_pickup_location_for_ride1, mock_dropoff_location_for_ride1):
    """Fixture for a ride request with location details included."""
    ride = mock_ride_requests[0].copy()
    ride["pickup_location"] = mock_pickup_location_for_ride1
    ride["dropoff_location"] = mock_dropoff_location_for_ride1
    return ride


class TestAvailableRides:
    """Test class for driver's ability to view available ride requests."""

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_available_rides_success(self, mock_require_user, mock_driver_data, 
                                         mock_ride_requests, mock_ride_with_locations):
        """Test successfully retrieving available ride requests."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for querying ride requests
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/query?status={RideStatus.REQUESTED.name}",
            json=mock_ride_requests,
            status=200
        )

        # Mock API responses for getting ride details with locations
        for ride in mock_ride_requests:
            # For simplicity, we'll use the same location details for all rides
            ride_with_locations = mock_ride_with_locations.copy()
            ride_with_locations["id"] = ride["id"]
            ride_with_locations["user_id"] = ride["user_id"]
            ride_with_locations["pickup_location_id"] = ride["pickup_location_id"]
            ride_with_locations["dropoff_location_id"] = ride["dropoff_location_id"]
            ride_with_locations["request_time"] = ride["request_time"]
            
            responses.add(
                responses.GET,
                f"{TEST_BASE_URL}/rides/{ride['id']}",
                json=ride_with_locations,
                status=200
            )

        # Call the function being tested
        results = RideService.get_available_rides(TEST_TOKEN)

        # Assertions
        assert len(results) == 3
        # Verify each ride has location details
        for ride in results:
            assert "pickup_location" in ride
            assert "dropoff_location" in ride
            assert ride["status"] == RideStatus.REQUESTED.name
            assert ride["driver_id"] is None  # No driver assigned yet

        # Verify mocks were called correctly
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        # One call for the query + one call per ride for details
        assert len(responses.calls) == 4

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_available_rides_empty(self, mock_require_user, mock_driver_data):
        """Test getting available rides when none are available."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for empty ride list
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/query?status={RideStatus.REQUESTED.name}",
            json=[],
            status=200
        )

        # Call the function being tested
        results = RideService.get_available_rides(TEST_TOKEN)

        # Assertions
        assert len(results) == 0
        assert isinstance(results, list)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 1  # Just one call to get rides

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_available_rides_not_found_response(self, mock_require_user, mock_driver_data):
        """Test handling of 404 response when no ride collection exists."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for 404 (no rides collection)
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/query?status={RideStatus.REQUESTED.name}",
            json={"error": "Collection not found"},
            status=404
        )

        # Call the function being tested
        results = RideService.get_available_rides(TEST_TOKEN)

        # Assertions
        assert len(results) == 0
        assert isinstance(results, list)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 1

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_available_rides_skip_invalid_ride(self, mock_require_user, mock_driver_data, 
                                                 mock_ride_requests, mock_ride_with_locations):
        """Test that rides with missing location data are gracefully skipped."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for querying ride requests
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/query?status={RideStatus.REQUESTED.name}",
            json=mock_ride_requests,
            status=200
        )

        # Mock the first ride to return successfully
        ride_with_locations = mock_ride_with_locations.copy()
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{mock_ride_requests[0]['id']}",
            json=ride_with_locations,
            status=200
        )

        # Mock the second ride to have an error
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{mock_ride_requests[1]['id']}",
            json={"error": "Location data not found"},
            status=500
        )

        # Mock the third ride to return successfully
        third_ride = mock_ride_with_locations.copy()
        third_ride["id"] = mock_ride_requests[2]["id"]
        third_ride["user_id"] = mock_ride_requests[2]["user_id"]
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{mock_ride_requests[2]['id']}",
            json=third_ride,
            status=200
        )

        # Call the function being tested
        results = RideService.get_available_rides(TEST_TOKEN)

        # Assertions
        assert len(results) == 2  # Only 2 of 3 rides should be returned
        # Verify the IDs of the returned rides
        assert results[0]["id"] == mock_ride_requests[0]["id"]
        assert results[1]["id"] == mock_ride_requests[2]["id"]
        
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 4  # Initial query + 3 get attempts

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_available_rides_unavailable_driver(self, mock_require_user, mock_unavailable_driver_data):
        """Test that unavailable drivers cannot see available rides."""
        # Setup mocks - driver is not available
        mock_require_user.return_value = mock_unavailable_driver_data

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.get_available_rides(TEST_TOKEN)

        # Verify the error message
        assert "must set your status to available" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 0  # No API calls should be made

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_available_rides_unverified_driver(self, mock_require_user, mock_unverified_driver_data):
        """Test that unverified drivers cannot see available rides."""
        # Setup mocks - driver is not verified
        mock_require_user.return_value = mock_unverified_driver_data

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.get_available_rides(TEST_TOKEN)

        # Verify the error message
        assert "must be verified" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 0  # No API calls should be made

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_available_rides_unauthorized(self, mock_require_user):
        """Test that non-drivers cannot see available rides."""
        # Setup mocks to simulate authorization failure
        mock_require_user.side_effect = AuthError("Access denied. This action requires driver user type")

        # Call the function and expect it to raise AuthError
        with pytest.raises(AuthError) as excinfo:
            RideService.get_available_rides(TEST_TOKEN)

        # Verify the error message
        assert "Access denied" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 0  # No API calls should be made

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_available_rides_server_error(self, mock_require_user, mock_driver_data):
        """Test handling of server errors."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API server error
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/query?status={RideStatus.REQUESTED.name}",
            json={"error": "Internal server error"},
            status=500
        )

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.get_available_rides(TEST_TOKEN)

        # Verify the error message
        assert "Failed to retrieve available rides" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 1  # One failed API call