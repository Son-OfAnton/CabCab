"""Tests for ride cancellation functionality in CabCab."""

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

@pytest.fixture
def mock_user_data():
    """Fixture for sample user data."""
    return {
        "id": TEST_USER_ID,
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "phone": "1234567890",
        "user_type": "passenger"
    }

@pytest.fixture
def mock_requested_ride():
    """Fixture for a ride in REQUESTED status."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_USER_ID,
        "pickup_location_id": "loc-123",
        "dropoff_location_id": "loc-456",
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
def mock_driver_assigned_ride():
    """Fixture for a ride in DRIVER_ASSIGNED status."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_USER_ID,
        "pickup_location_id": "loc-123",
        "dropoff_location_id": "loc-456",
        "status": RideStatus.DRIVER_ASSIGNED.name,
        "estimated_fare": 25.50,
        "distance": 8.2,
        "duration": 18,
        "driver_id": "driver-789",
        "request_time": "2023-06-01T14:30:00",
        "start_time": None,
        "end_time": None,
        "actual_fare": None,
        "payment_id": None,
        "rating": None,
        "feedback": None
    }

@pytest.fixture
def mock_in_progress_ride():
    """Fixture for a ride in IN_PROGRESS status."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_USER_ID,
        "pickup_location_id": "loc-123",
        "dropoff_location_id": "loc-456",
        "status": RideStatus.IN_PROGRESS.name,
        "estimated_fare": 25.50,
        "distance": 8.2,
        "duration": 18,
        "driver_id": "driver-789",
        "request_time": "2023-06-01T14:30:00",
        "start_time": "2023-06-01T14:45:00",
        "end_time": None,
        "actual_fare": None,
        "payment_id": None,
        "rating": None,
        "feedback": None
    }

@pytest.fixture
def mock_another_user_ride():
    """Fixture for a ride belonging to another user."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": "another-user-id",
        "pickup_location_id": "loc-123",
        "dropoff_location_id": "loc-456",
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

class TestRideCancel:
    """Test class for ride cancellation functionality."""
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_cancel_ride_requested_status(self, mock_verify_token, mock_user_data, mock_requested_ride):
        """Test successful cancellation of a ride in REQUESTED status."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Mock API getting the existing ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_requested_ride,
            status=200
        )
        
        # Expected cancelled ride data
        cancelled_ride = mock_requested_ride.copy()
        cancelled_ride["status"] = RideStatus.CANCELLED.name
        
        # Mock API for updating the ride
        responses.add(
            responses.PUT,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=cancelled_ride,
            status=200,
            match=[lambda request: json.loads(request.body)["status"] == RideStatus.CANCELLED.name]
        )
        
        # Call the function being tested
        result = RideService.cancel_ride(TEST_TOKEN, TEST_RIDE_ID)
        
        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["user_id"] == TEST_USER_ID
        assert result["status"] == RideStatus.CANCELLED.name
        
        # Verify mocks were called correctly
        mock_verify_token.assert_called_once_with(TEST_TOKEN)
        assert len(responses.calls) == 2  # One GET and one PUT request
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_cancel_ride_driver_assigned_status(self, mock_verify_token, mock_user_data, mock_driver_assigned_ride):
        """Test successful cancellation of a ride in DRIVER_ASSIGNED status."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Mock API getting the existing ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_driver_assigned_ride,
            status=200
        )
        
        # Expected cancelled ride data
        cancelled_ride = mock_driver_assigned_ride.copy()
        cancelled_ride["status"] = RideStatus.CANCELLED.name
        
        # Mock API for updating the ride
        responses.add(
            responses.PUT,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=cancelled_ride,
            status=200
        )
        
        # Call the function being tested
        result = RideService.cancel_ride(TEST_TOKEN, TEST_RIDE_ID)
        
        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["user_id"] == TEST_USER_ID
        assert result["status"] == RideStatus.CANCELLED.name
        assert "driver_id" in result  # Driver ID should still be present
        
        # Verify mocks were called correctly
        mock_verify_token.assert_called_once_with(TEST_TOKEN)
        assert len(responses.calls) == 2  # One GET and one PUT request
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_cancel_ride_unauthorized(self, mock_verify_token):
        """Test that an unauthorized user cannot cancel a ride."""
        # Setup mock to simulate authorization failure
        mock_verify_token.side_effect = AuthError("Invalid or expired token")
        
        # Call the function and expect it to raise AuthError
        with pytest.raises(AuthError) as excinfo:
            RideService.cancel_ride("invalid_token", TEST_RIDE_ID)
        
        # Verify the error message
        assert "Invalid or expired token" in str(excinfo.value)
        
        # Verify mock was called
        mock_verify_token.assert_called_once_with("invalid_token")
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_cancel_ride_not_found(self, mock_verify_token, mock_user_data):
        """Test error handling when ride is not found."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Mock API returning 404 for non-existent ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json={"error": "Ride not found"},
            status=404
        )
        
        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.cancel_ride(TEST_TOKEN, TEST_RIDE_ID)
        
        # Verify the error message
        assert "Ride with ID" in str(excinfo.value)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_cancel_another_users_ride(self, mock_verify_token, mock_user_data, mock_another_user_ride):
        """Test that a user cannot cancel another user's ride."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Mock API getting a ride belonging to another user
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_another_user_ride,
            status=200
        )
        
        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.cancel_ride(TEST_TOKEN, TEST_RIDE_ID)
        
        # Verify the error message
        assert "permission to cancel" in str(excinfo.value)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_cancel_ride_invalid_status(self, mock_verify_token, mock_user_data, mock_in_progress_ride):
        """Test that a ride cannot be cancelled if in an invalid status."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Mock API getting a ride that's already in progress
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_in_progress_ride,
            status=200
        )
        
        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.cancel_ride(TEST_TOKEN, TEST_RIDE_ID)
        
        # Verify the error message
        assert "Cannot cancel ride with status" in str(excinfo.value)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_cancel_ride_api_error(self, mock_verify_token, mock_user_data, mock_requested_ride):
        """Test handling of API error during ride cancellation."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Mock API getting the existing ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_requested_ride,
            status=200
        )
        
        # Mock API returning error when trying to update the ride
        responses.add(
            responses.PUT,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json={"error": "Server error"},
            status=500
        )
        
        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.cancel_ride(TEST_TOKEN, TEST_RIDE_ID)
        
        # Verify the error message
        assert "Failed to cancel ride" in str(excinfo.value)