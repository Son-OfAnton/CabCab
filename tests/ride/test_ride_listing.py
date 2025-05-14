"""Tests for ride listing functionality in CabCab."""

import pytest
import json
import responses
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.services.ride_service import RideService, RideServiceError
from app.services.auth_service import AuthService, AuthError
from app.models.ride import RideStatus

# Constants for testing
TEST_BASE_URL = "http://localhost:3000"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzNDUtNjc4OTAtYWJjZGUtZWZnaGkiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTYwMDAwMDAwMH0.3GRZ-mDRrO7CYJhOBARgPCu7tVUFo9hFS7G4pVX2k1k"
TEST_USER_ID = "12345-67890-abcde-efghi"

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
def mock_ride_list():
    """Fixture for a list of rides belonging to a user."""
    now = datetime.now()
    
    return [
        {
            "id": "ride-001",
            "user_id": TEST_USER_ID,
            "pickup_location_id": "loc-123",
            "dropoff_location_id": "loc-456",
            "status": RideStatus.COMPLETED.name,
            "estimated_fare": 25.50,
            "distance": 8.2,
            "duration": 18,
            "driver_id": "driver-789",
            "request_time": (now - timedelta(days=2)).isoformat(),
            "start_time": (now - timedelta(days=2, minutes=15)).isoformat(),
            "end_time": (now - timedelta(days=2, minutes=40)).isoformat(),
            "actual_fare": 27.80,
            "payment_id": "payment-001",
            "rating": 5,
            "feedback": "Great ride!"
        },
        {
            "id": "ride-002",
            "user_id": TEST_USER_ID,
            "pickup_location_id": "loc-789",
            "dropoff_location_id": "loc-012",
            "status": RideStatus.CANCELLED.name,
            "estimated_fare": 15.75,
            "distance": 4.5,
            "duration": 12,
            "driver_id": None,
            "request_time": (now - timedelta(days=1)).isoformat(),
            "start_time": None,
            "end_time": None,
            "actual_fare": None,
            "payment_id": None,
            "rating": None,
            "feedback": None
        },
        {
            "id": "ride-003",
            "user_id": TEST_USER_ID,
            "pickup_location_id": "loc-345",
            "dropoff_location_id": "loc-678",
            "status": RideStatus.REQUESTED.name,
            "estimated_fare": 35.25,
            "distance": 12.3,
            "duration": 28,
            "driver_id": None,
            "request_time": now.isoformat(),
            "start_time": None,
            "end_time": None,
            "actual_fare": None,
            "payment_id": None,
            "rating": None,
            "feedback": None
        }
    ]

@pytest.fixture
def mock_completed_rides():
    """Fixture for a list of completed rides."""
    now = datetime.now()
    
    return [
        {
            "id": "ride-001",
            "user_id": TEST_USER_ID,
            "pickup_location_id": "loc-123",
            "dropoff_location_id": "loc-456",
            "status": RideStatus.COMPLETED.name,
            "estimated_fare": 25.50,
            "distance": 8.2,
            "duration": 18,
            "driver_id": "driver-789",
            "request_time": (now - timedelta(days=2)).isoformat(),
            "start_time": (now - timedelta(days=2, minutes=15)).isoformat(),
            "end_time": (now - timedelta(days=2, minutes=40)).isoformat(),
            "actual_fare": 27.80,
            "payment_id": "payment-001",
            "rating": 5,
            "feedback": "Great ride!"
        },
        {
            "id": "ride-004",
            "user_id": TEST_USER_ID,
            "pickup_location_id": "loc-901",
            "dropoff_location_id": "loc-234",
            "status": RideStatus.COMPLETED.name,
            "estimated_fare": 18.25,
            "distance": 5.7,
            "duration": 15,
            "driver_id": "driver-456",
            "request_time": (now - timedelta(days=5)).isoformat(),
            "start_time": (now - timedelta(days=5, minutes=10)).isoformat(),
            "end_time": (now - timedelta(days=5, minutes=30)).isoformat(),
            "actual_fare": 19.50,
            "payment_id": "payment-002",
            "rating": 4,
            "feedback": "Good service"
        }
    ]

class TestRideListing:
    """Test class for ride listing functionality."""
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_get_user_rides_all(self, mock_verify_token, mock_require_user, mock_user_data, mock_ride_list):
        """Test retrieving all rides for a passenger."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        mock_require_user.return_value = mock_user_data
        
        # Mock API response for getting user rides
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/query?user_id={TEST_USER_ID}",
            json=mock_ride_list,
            status=200
        )
        
        # Call the function being tested
        results = RideService.get_user_rides(TEST_TOKEN)
        
        # Assertions
        assert len(results) == 3
        # Verify rides are sorted by request_time, most recent first
        assert results[0]["id"] == "ride-003"  # Most recent
        assert results[1]["id"] == "ride-002"  
        assert results[2]["id"] == "ride-001"  # Oldest
        
        # Verify fields are present in each ride
        for ride in results:
            assert "id" in ride
            assert "status" in ride
            assert "request_time" in ride
            assert ride["user_id"] == TEST_USER_ID
        
        # Verify mock was called correctly
        mock_verify_token.assert_called_once_with(TEST_TOKEN)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_get_user_rides_with_status_filter(self, mock_verify_token, mock_require_user, 
                                            mock_user_data, mock_completed_rides):
        """Test retrieving rides filtered by status."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        mock_require_user.return_value = mock_user_data
        
        # Mock API response for getting filtered user rides
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/query?user_id={TEST_USER_ID}&status={RideStatus.COMPLETED.name}",
            json=mock_completed_rides,
            status=200
        )
        
        # Call the function being tested with status filter
        results = RideService.get_user_rides(TEST_TOKEN, RideStatus.COMPLETED.name)
        
        # Assertions
        assert len(results) == 2
        # Verify all returned rides have the correct status
        for ride in results:
            assert ride["status"] == RideStatus.COMPLETED.name
        
        # Verify rides are sorted by request_time, most recent first
        assert results[0]["id"] == "ride-001"  # More recent completed ride
        assert results[1]["id"] == "ride-004"  # Older completed ride
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_get_user_rides_empty_list(self, mock_verify_token, mock_require_user, mock_user_data):
        """Test behavior when user has no rides."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        mock_require_user.return_value = mock_user_data
        
        # Mock API response for empty ride list
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/query?user_id={TEST_USER_ID}",
            json=[],
            status=200
        )
        
        # Call the function being tested
        results = RideService.get_user_rides(TEST_TOKEN)
        
        # Assertions
        assert len(results) == 0
        assert isinstance(results, list)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_get_user_rides_not_found_response(self, mock_verify_token, mock_require_user, mock_user_data):
        """Test behavior when the API returns a 404."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        mock_require_user.return_value = mock_user_data
        
        # Mock API response for 404 (no rides collection)
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/query?user_id={TEST_USER_ID}",
            json={"error": "Collection not found"},
            status=404
        )
        
        # Call the function being tested
        results = RideService.get_user_rides(TEST_TOKEN)
        
        # Assertions
        assert len(results) == 0
        assert isinstance(results, list)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_get_user_rides_unauthorized(self, mock_verify_token):
        """Test that an unauthorized user cannot list rides."""
        # Setup mock to simulate authorization failure
        mock_verify_token.side_effect = AuthError("Invalid or expired token")
        
        # Call the function and expect it to raise AuthError
        with pytest.raises(AuthError) as excinfo:
            RideService.get_user_rides("invalid_token")
        
        # Verify the error message
        assert "Invalid or expired token" in str(excinfo.value)
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    @patch('app.services.auth_service.AuthService.verify_token')
    def test_get_user_rides_server_error(self, mock_verify_token, mock_require_user, mock_user_data):
        """Test handling of server errors."""
        # Setup mocks
        mock_verify_token.return_value = mock_user_data
        mock_require_user.return_value = mock_user_data
        
        # Mock API server error
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/rides/query?user_id={TEST_USER_ID}",
            json={"error": "Internal server error"},
            status=500
        )
        
        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.get_user_rides(TEST_TOKEN)
        
        # Verify the error message
        assert "Failed to retrieve rides" in str(excinfo.value)