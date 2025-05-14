"""Tests for the driver ride details viewing feature in CabCab."""

import pytest
import json
import responses
from unittest.mock import patch, MagicMock
from app.services.ride_service import RideService, RideServiceError
from app.services.auth_service import AuthService, AuthError, UserType
from app.models.ride import RideStatus

# Constants for testing
TEST_BASE_URL = "http://localhost:3000"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZHJpdmVyLTEyMzQ1IiwidXNlcl90eXBlIjoiZHJpdmVyIiwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjE2MDAwMDAwMDB9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
TEST_DRIVER_ID = "driver-12345"
TEST_RIDE_ID = "ride-67890"
TEST_PASSENGER_ID = "passenger-54321"


@pytest.fixture
def mock_driver_data():
    """Fixture for sample verified driver data."""
    return {
        "id": TEST_DRIVER_ID,
        "email": "driver@example.com",
        "first_name": "Test",
        "last_name": "Driver",
        "phone": "1234567890",
        "user_type": "driver",
        "license_number": "DL123456",
        "is_verified": True,
        "is_available": True,
        "rating": 4.8,
        "rating_count": 25,
        "vehicle_id": "vehicle-789",
        "created_at": "2023-01-01T12:00:00",
        "updated_at": "2023-01-01T12:30:00"
    }


@pytest.fixture
def mock_passenger_data():
    """Fixture for the passenger data."""
    return {
        "id": TEST_PASSENGER_ID,
        "email": "passenger@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "9876543210",
        "user_type": "passenger",
        "rating": 4.5,
        "rating_count": 10,
        "created_at": "2023-01-01T10:00:00",
        "updated_at": "2023-01-01T10:30:00"
    }


@pytest.fixture
def mock_pickup_location():
    """Fixture for pickup location."""
    return {
        "id": "loc-pickup-123",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "USA",
        "user_id": TEST_PASSENGER_ID
    }


@pytest.fixture
def mock_dropoff_location():
    """Fixture for dropoff location."""
    return {
        "id": "loc-dropoff-456",
        "latitude": 40.7581,
        "longitude": -73.9855,
        "address": "456 Broadway",
        "city": "New York",
        "state": "NY",
        "postal_code": "10012",
        "country": "USA",
        "user_id": TEST_PASSENGER_ID
    }


@pytest.fixture
def mock_requested_ride(mock_pickup_location, mock_dropoff_location):
    """Fixture for a ride in REQUESTED status."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_PASSENGER_ID,
        "pickup_location_id": mock_pickup_location["id"],
        "dropoff_location_id": mock_dropoff_location["id"],
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
        "feedback": None,
        "pickup_location": mock_pickup_location,
        "dropoff_location": mock_dropoff_location
    }


@pytest.fixture
def mock_assigned_ride(mock_pickup_location, mock_dropoff_location):
    """Fixture for a ride in DRIVER_ASSIGNED status."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_PASSENGER_ID,
        "pickup_location_id": mock_pickup_location["id"],
        "dropoff_location_id": mock_dropoff_location["id"],
        "status": RideStatus.DRIVER_ASSIGNED.name,
        "estimated_fare": 25.50,
        "distance": 8.2,
        "duration": 18,
        "driver_id": TEST_DRIVER_ID,
        "request_time": "2023-06-01T14:30:00",
        "start_time": None,
        "end_time": None,
        "actual_fare": None,
        "payment_id": None,
        "rating": None,
        "feedback": None,
        "pickup_location": mock_pickup_location,
        "dropoff_location": mock_dropoff_location
    }


@pytest.fixture
def mock_ride_another_driver(mock_pickup_location, mock_dropoff_location):
    """Fixture for a ride assigned to another driver."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_PASSENGER_ID,
        "pickup_location_id": mock_pickup_location["id"],
        "dropoff_location_id": mock_dropoff_location["id"],
        "status": RideStatus.DRIVER_ASSIGNED.name,
        "estimated_fare": 25.50,
        "distance": 8.2,
        "duration": 18,
        "driver_id": "other-driver-123",
        "request_time": "2023-06-01T14:30:00",
        "start_time": None,
        "end_time": None,
        "actual_fare": None,
        "payment_id": None,
        "rating": None,
        "feedback": None,
        "pickup_location": mock_pickup_location,
        "dropoff_location": mock_dropoff_location
    }


class TestDriverRideDetails:
    """Test class for driver's ability to view details of a specific ride."""

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_ride_details_requested(self, mock_require_user, mock_driver_data, 
                                        mock_requested_ride, mock_passenger_data):
        """Test retrieving details of a ride in REQUESTED status."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_requested_ride,
            status=200
        )

        # Mock API response for getting passenger details
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/{TEST_PASSENGER_ID}",
            json=mock_passenger_data,
            status=200
        )

        # Call the function being tested - assume there's a method for drivers to get ride details
        # The method signature might be different, adjust as needed
        result = RideService.get_ride_details_for_driver(TEST_TOKEN, TEST_RIDE_ID)

        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["status"] == RideStatus.REQUESTED.name
        assert result["driver_id"] is None  # No driver assigned yet

        # Check that pickup and dropoff locations are included
        assert "pickup_location" in result
        assert result["pickup_location"]["address"] == "123 Main St"
        assert "dropoff_location" in result
        assert result["dropoff_location"]["address"] == "456 Broadway"

        # Check that passenger details are included
        assert "passenger" in result
        assert result["passenger"]["id"] == TEST_PASSENGER_ID
        assert result["passenger"]["first_name"] == "John"
        assert result["passenger"]["last_name"] == "Doe"
        assert result["passenger"]["phone"] == "9876543210"
        assert result["passenger"]["rating"] == 4.5

        # Verify mocks were called correctly
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 2  # One GET for ride, one GET for passenger

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_assigned_ride_details(self, mock_require_user, mock_driver_data, 
                                      mock_assigned_ride, mock_passenger_data):
        """Test retrieving details of a ride assigned to the current driver."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_assigned_ride,
            status=200
        )

        # Mock API response for getting passenger details
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/{TEST_PASSENGER_ID}",
            json=mock_passenger_data,
            status=200
        )

        # Call the function being tested
        result = RideService.get_ride_details_for_driver(TEST_TOKEN, TEST_RIDE_ID)

        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["status"] == RideStatus.DRIVER_ASSIGNED.name
        assert result["driver_id"] == TEST_DRIVER_ID  # Ride assigned to this driver

        # Check that pickup and dropoff locations are included
        assert "pickup_location" in result
        assert result["pickup_location"]["address"] == "123 Main St"
        assert "dropoff_location" in result
        assert result["dropoff_location"]["address"] == "456 Broadway"

        # Check that passenger details are included
        assert "passenger" in result
        assert result["passenger"]["id"] == TEST_PASSENGER_ID
        assert result["passenger"]["first_name"] == "John"
        assert result["passenger"]["last_name"] == "Doe"

        # Verify mocks were called correctly
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 2  # One GET for ride, one GET for passenger

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_ride_details_another_driver(self, mock_require_user, mock_driver_data, mock_ride_another_driver):
        """Test that a driver cannot see details of a ride assigned to another driver."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_ride_another_driver,
            status=200
        )

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.get_ride_details_for_driver(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message
        assert "assigned to another driver" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 1  # Only one GET for ride

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_ride_details_not_found(self, mock_require_user, mock_driver_data):
        """Test handling when a ride is not found."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for non-existent ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json={"error": "Ride not found"},
            status=404
        )

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.get_ride_details_for_driver(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message
        assert "not found" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 1  # Only one GET for ride

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_ride_details_unauthorized(self, mock_require_user):
        """Test that non-drivers cannot view ride details."""
        # Setup mocks to simulate authorization failure
        mock_require_user.side_effect = AuthError("Access denied. This action requires driver user type")

        # Call the function and expect it to raise AuthError
        with pytest.raises(AuthError) as excinfo:
            RideService.get_ride_details_for_driver(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message
        assert "Access denied" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 0  # No API calls should be made

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_ride_details_passenger_not_found(self, mock_require_user, mock_driver_data, mock_requested_ride):
        """Test handling when passenger details cannot be retrieved."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_requested_ride,
            status=200
        )

        # Mock API response for passenger not found
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/{TEST_PASSENGER_ID}",
            json={"error": "User not found"},
            status=404
        )

        # Call the function - should succeed but with limited passenger info
        result = RideService.get_ride_details_for_driver(TEST_TOKEN, TEST_RIDE_ID)

        # Assertions - should still get ride details, but passenger info might be limited
        assert result["id"] == TEST_RIDE_ID
        assert result["status"] == RideStatus.REQUESTED.name
        # Check that we have a fallback for passenger information
        assert "passenger" in result
        assert result["passenger"]["id"] == TEST_PASSENGER_ID  # At least the ID should be there
        
        # Or if the implementation completely excludes passenger info on error:
        # assert "passenger" not in result

        # Verify mocks were called correctly
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 2  # One GET for ride, one failed GET for passenger

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_get_ride_details_server_error(self, mock_require_user, mock_driver_data):
        """Test handling of server errors."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API server error when getting ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json={"error": "Internal server error"},
            status=500
        )

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.get_ride_details_for_driver(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message
        assert "Failed to retrieve ride" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 1  # One failed GET