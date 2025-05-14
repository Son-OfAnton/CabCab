"""Tests for the driver ride acceptance feature in CabCab."""

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
        "feedback": None
    }


@pytest.fixture
def mock_already_accepted_ride(mock_pickup_location, mock_dropoff_location):
    """Fixture for a ride that's already been accepted by another driver."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_PASSENGER_ID,
        "pickup_location_id": mock_pickup_location["id"],
        "dropoff_location_id": mock_dropoff_location["id"],
        "status": RideStatus.DRIVER_ASSIGNED.name,
        "estimated_fare": 25.50,
        "distance": 8.2,
        "duration": 18,
        "driver_id": "other-driver-123",  # Already accepted by another driver
        "request_time": "2023-06-01T14:30:00",
        "start_time": None,
        "end_time": None,
        "actual_fare": None,
        "payment_id": None,
        "rating": None,
        "feedback": None
    }


@pytest.fixture
def mock_cancelled_ride(mock_pickup_location, mock_dropoff_location):
    """Fixture for a cancelled ride."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_PASSENGER_ID,
        "pickup_location_id": mock_pickup_location["id"],
        "dropoff_location_id": mock_dropoff_location["id"],
        "status": RideStatus.CANCELLED.name,
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
def mock_accepted_ride_response(mock_requested_ride, mock_pickup_location, mock_dropoff_location):
    """Fixture for the response after a successful ride acceptance."""
    accepted_ride = mock_requested_ride.copy()
    accepted_ride["status"] = RideStatus.DRIVER_ASSIGNED.name
    accepted_ride["driver_id"] = TEST_DRIVER_ID
    accepted_ride["pickup_location"] = mock_pickup_location
    accepted_ride["dropoff_location"] = mock_dropoff_location
    return accepted_ride


class TestAcceptRide:
    """Test class for driver's ability to accept rides."""

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_accept_ride_successful(self, mock_require_user, mock_driver_data, 
                                   mock_requested_ride, mock_accepted_ride_response, 
                                   mock_pickup_location, mock_dropoff_location):
        """Test successfully accepting a ride."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_requested_ride,
            status=200
        )

        # Expected data in the ride update (after accepting)
        expected_update = mock_requested_ride.copy()
        expected_update["driver_id"] = TEST_DRIVER_ID
        expected_update["status"] = RideStatus.DRIVER_ASSIGNED.name

        # Mock API for updating the ride
        def request_callback(request):
            payload = json.loads(request.body)
            # Verify key fields were updated correctly
            assert payload["status"] == RideStatus.DRIVER_ASSIGNED.name
            assert payload["driver_id"] == TEST_DRIVER_ID
            return (200, {}, json.dumps(expected_update))

        responses.add_callback(
            responses.PUT,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            callback=request_callback,
            content_type="application/json"
        )

        # Mock API for getting locations for the detailed ride data
        responses.add(
            responses.GET, 
            f"{TEST_BASE_URL}/locations/{mock_pickup_location['id']}", 
            json=mock_pickup_location, 
            status=200
        )
        responses.add(
            responses.GET, 
            f"{TEST_BASE_URL}/locations/{mock_dropoff_location['id']}", 
            json=mock_dropoff_location, 
            status=200
        )

        # Mock API for getting the ride details after update
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=expected_update,
            status=200
        )

        # Call the function being tested
        result = RideService.accept_ride(TEST_TOKEN, TEST_RIDE_ID)

        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["status"] == RideStatus.DRIVER_ASSIGNED.name
        assert result["driver_id"] == TEST_DRIVER_ID

        # Verify mocks were called correctly
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        # There should be 4 total calls: 
        # 1. GET ride
        # 2. PUT update ride
        # 3-4. GET locations or GET updated ride
        assert len(responses.calls) >= 3

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_accept_ride_unverified_driver(self, mock_require_user, mock_unverified_driver_data):
        """Test that an unverified driver cannot accept rides."""
        # Setup mocks - driver is not verified
        mock_require_user.return_value = mock_unverified_driver_data

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.accept_ride(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message
        assert "must be verified" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 0  # No API calls should be made

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_accept_ride_unavailable_driver(self, mock_require_user, mock_unavailable_driver_data):
        """Test that an unavailable driver cannot accept rides."""
        # Setup mocks - driver is not available
        mock_require_user.return_value = mock_unavailable_driver_data

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.accept_ride(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message
        assert "must set your status to available" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 0  # No API calls should be made

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_accept_already_accepted_ride(self, mock_require_user, mock_driver_data, 
                                         mock_already_accepted_ride):
        """Test that a ride already accepted by another driver cannot be accepted again."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for getting an already accepted ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_already_accepted_ride,
            status=200
        )

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.accept_ride(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message
        assert "already been accepted" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 1  # One GET for ride details

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_accept_cancelled_ride(self, mock_require_user, mock_driver_data, mock_cancelled_ride):
        """Test that a cancelled ride cannot be accepted."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for getting a cancelled ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_cancelled_ride,
            status=200
        )

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.accept_ride(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message
        assert "Cannot accept ride with status" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 1  # One GET for ride details

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_accept_ride_not_found(self, mock_require_user, mock_driver_data):
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
            RideService.accept_ride(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message contains ride ID and "not found"
        assert "not found" in str(excinfo.value).lower()
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 1  # One failed GET for ride

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_accept_ride_unauthorized(self, mock_require_user):
        """Test that non-drivers cannot accept rides."""
        # Setup mocks to simulate authorization failure
        mock_require_user.side_effect = AuthError("Access denied. This action requires driver user type")

        # Call the function and expect it to raise AuthError
        with pytest.raises(AuthError) as excinfo:
            RideService.accept_ride(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message
        assert "Access denied" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 0  # No API calls should be made

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_accept_ride_update_error(self, mock_require_user, mock_driver_data, mock_requested_ride):
        """Test handling of server errors during ride update."""
        # Setup mocks
        mock_require_user.return_value = mock_driver_data

        # Mock API response for getting the ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_requested_ride,
            status=200
        )

        # Mock API error for updating the ride
        responses.add(
            responses.PUT,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json={"error": "Server error"},
            status=500
        )

        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.accept_ride(TEST_TOKEN, TEST_RIDE_ID)

        # Verify the error message
        assert "Failed to accept ride" in str(excinfo.value)
        mock_require_user.assert_called_once_with(TEST_TOKEN, [UserType.DRIVER.value])
        assert len(responses.calls) == 2  # One GET for ride, one failed PUT