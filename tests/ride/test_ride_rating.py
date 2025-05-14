"""Tests for ride rating functionality in CabCab."""

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
def mock_completed_ride():
    """Fixture for a completed ride that can be rated."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_USER_ID,
        "pickup_location_id": "loc-123",
        "dropoff_location_id": "loc-456",
        "status": RideStatus.COMPLETED.name,
        "estimated_fare": 25.50,
        "distance": 8.2,
        "duration": 18,
        "driver_id": TEST_DRIVER_ID,
        "request_time": "2023-06-01T14:30:00",
        "start_time": "2023-06-01T14:45:00",
        "end_time": "2023-06-01T15:05:00",
        "actual_fare": 27.50,
        "payment_id": "payment-123",
        "rating": None,
        "feedback": None
    }

@pytest.fixture
def mock_already_rated_ride():
    """Fixture for a completed ride that has already been rated."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_USER_ID,
        "pickup_location_id": "loc-123",
        "dropoff_location_id": "loc-456",
        "status": RideStatus.COMPLETED.name,
        "estimated_fare": 25.50,
        "distance": 8.2,
        "duration": 18,
        "driver_id": TEST_DRIVER_ID,
        "request_time": "2023-06-01T14:30:00",
        "start_time": "2023-06-01T14:45:00",
        "end_time": "2023-06-01T15:05:00",
        "actual_fare": 27.50,
        "payment_id": "payment-123",
        "rating": 4,
        "feedback": "Good ride"
    }

@pytest.fixture
def mock_in_progress_ride():
    """Fixture for a ride that is still in progress (can't be rated)."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": TEST_USER_ID,
        "pickup_location_id": "loc-123",
        "dropoff_location_id": "loc-456",
        "status": RideStatus.IN_PROGRESS.name,
        "estimated_fare": 25.50,
        "distance": 8.2,
        "duration": 18,
        "driver_id": TEST_DRIVER_ID,
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
    """Fixture for a completed ride belonging to a different user."""
    return {
        "id": TEST_RIDE_ID,
        "user_id": "other-user-id",
        "pickup_location_id": "loc-123",
        "dropoff_location_id": "loc-456",
        "status": RideStatus.COMPLETED.name,
        "estimated_fare": 25.50,
        "distance": 8.2,
        "duration": 18,
        "driver_id": TEST_DRIVER_ID,
        "request_time": "2023-06-01T14:30:00",
        "start_time": "2023-06-01T14:45:00",
        "end_time": "2023-06-01T15:05:00",
        "actual_fare": 27.50,
        "payment_id": "payment-123",
        "rating": None,
        "feedback": None
    }

class TestRideRating:
    """Test class for ride rating functionality."""
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_rate_ride_successful(self, mock_verify_token, mock_user_data, mock_completed_ride):
        """Test successful rating of a completed ride."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Rating values to submit
        rating = 5
        feedback = "Excellent ride, very professional driver!"
        
        # Mock API response for getting the existing ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_completed_ride,
            status=200
        )
        
        # Expected result after rating update
        updated_ride = mock_completed_ride.copy()
        updated_ride["rating"] = rating
        updated_ride["feedback"] = feedback
        
        # Mock API response for updating the ride
        responses.add(
            responses.PUT,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=updated_ride,
            status=200,
            match=[lambda request: json.loads(request.body)["rating"] == rating]
        )
        
        # Call the function being tested
        result = RideService.rate_ride(TEST_TOKEN, TEST_RIDE_ID, rating, feedback)
        
        # Assertions
        assert result["id"] == TEST_RIDE_ID
        assert result["rating"] == rating
        assert result["feedback"] == feedback
        
        # Verify all API calls were made
        assert len(responses.calls) == 2  # One GET for ride, one PUT to update
        
        # Check that all necessary fields remain intact
        assert result["status"] == RideStatus.COMPLETED.name
        assert result["user_id"] == TEST_USER_ID
        assert result["driver_id"] == TEST_DRIVER_ID
        assert result["actual_fare"] == 27.50
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_rate_ride_already_rated(self, mock_verify_token, mock_user_data, mock_already_rated_ride):
        """Test handling when trying to rate a ride that's already rated."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Rating values to submit
        rating = 3
        feedback = "Changed my mind, it was just ok"
        
        # Mock API response for getting the already rated ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_already_rated_ride,
            status=200
        )
        
        # Call the function and expect it to raise an error
        with pytest.raises(RideServiceError) as excinfo:
            RideService.rate_ride(TEST_TOKEN, TEST_RIDE_ID, rating, feedback)
        
        # Verify the error message
        assert "already been rated" in str(excinfo.value)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_rate_ride_not_completed(self, mock_verify_token, mock_user_data, mock_in_progress_ride):
        """Test handling when trying to rate a ride that's not completed."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Rating values to submit
        rating = 5
        feedback = "Great so far!"
        
        # Mock API response for getting the in-progress ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_in_progress_ride,
            status=200
        )
        
        # Call the function and expect it to raise an error
        with pytest.raises(RideServiceError) as excinfo:
            RideService.rate_ride(TEST_TOKEN, TEST_RIDE_ID, rating, feedback)
        
        # Verify the error message
        assert "Only completed rides can be rated" in str(excinfo.value)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_rate_another_user_ride(self, mock_verify_token, mock_user_data, mock_another_user_ride):
        """Test handling when trying to rate another user's ride."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Rating values to submit
        rating = 5
        feedback = "Excellent ride"
        
        # Mock API response for getting a ride belonging to another user
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_another_user_ride,
            status=200
        )
        
        # Call the function and expect it to raise an error
        with pytest.raises(RideServiceError) as excinfo:
            RideService.rate_ride(TEST_TOKEN, TEST_RIDE_ID, rating, feedback)
        
        # Verify the error message
        assert "permission to rate" in str(excinfo.value)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_rate_ride_invalid_rating(self, mock_verify_token, mock_user_data, mock_completed_ride):
        """Test handling of invalid rating values."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Invalid ratings to test
        invalid_ratings = [-1, 0, 6, 10]
        
        # Mock API response for getting the ride (needed for each test)
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_completed_ride,
            status=200
        )
        
        # Test each invalid rating
        for invalid_rating in invalid_ratings:
            with pytest.raises(RideServiceError) as excinfo:
                RideService.rate_ride(TEST_TOKEN, TEST_RIDE_ID, invalid_rating, "Test feedback")
            
            # Verify the error message
            assert "Rating must be between 1 and 5" in str(excinfo.value)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_rate_ride_not_found(self, mock_verify_token, mock_user_data):
        """Test error handling when ride is not found."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Rating values to submit
        rating = 5
        feedback = "Great ride!"
        
        # Mock API response for non-existent ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json={"error": "Ride not found"},
            status=404
        )
        
        # Call the function and expect it to raise an error
        with pytest.raises(RideServiceError) as excinfo:
            RideService.rate_ride(TEST_TOKEN, TEST_RIDE_ID, rating, feedback)
        
        # Verify the error message
        assert f"Ride with ID {TEST_RIDE_ID} not found" in str(excinfo.value)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_rate_ride_server_error(self, mock_verify_token, mock_user_data, mock_completed_ride):
        """Test handling of server error during rating update."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        
        # Rating values to submit
        rating = 5
        feedback = "Great ride!"
        
        # Mock API response for getting the existing ride
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json=mock_completed_ride,
            status=200
        )
        
        # Mock API server error when updating the ride
        responses.add(
            responses.PUT,
            f"{TEST_BASE_URL}/rides/{TEST_RIDE_ID}",
            json={"error": "Internal server error"},
            status=500
        )
        
        # Call the function and expect it to raise an error
        with pytest.raises(RideServiceError) as excinfo:
            RideService.rate_ride(TEST_TOKEN, TEST_RIDE_ID, rating, feedback)
        
        # Verify the error message
        assert "Failed to rate ride" in str(excinfo.value)
    
    @responses.activate
    def test_rate_ride_unauthorized(self):
        """Test that an unauthorized user cannot rate a ride."""
        # Mock authentication error by not setting up verify_token mock
        with pytest.raises(AuthError) as excinfo:
            RideService.rate_ride("invalid_token", TEST_RIDE_ID, 5, "Great ride!")
        
        # Verify no API calls were made because authentication failed early
        assert len(responses.calls) == 0