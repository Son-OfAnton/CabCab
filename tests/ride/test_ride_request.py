"""Tests for ride request functionality in CabCab."""

import pytest
import json
import uuid
import responses
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.services.ride_service import RideService, RideServiceError
from app.services.auth_service import AuthError
from app.models.ride import RideStatus

# Constants for testing
TEST_BASE_URL = "http://localhost:3000"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzNDUtNjc4OTAtYWJjZGUtZWZnaGkiLCJ1c2VyX3R5cGUiOiJwYXNzZW5nZXIiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTYwMDAwMDAwMH0.3GRZ-mDRrO7CYJhOBARgPCu7tVUFo9hFS7G4pVX2k1k"
TEST_USER_ID = "12345-67890-abcde-efghi"

# Sample test data
TEST_PICKUP = {
    "address": "123 Main St",
    "city": "Boston",
    "state": "MA",
    "postal": "02108",
    "country": "USA"
}

TEST_DROPOFF = {
    "address": "456 Elm St",
    "city": "Cambridge",
    "state": "MA",
    "postal": "02139",
    "country": "USA"
}

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
def mock_uuid():
    """Mock for uuid4 to return predictable IDs."""
    with patch('uuid.uuid4', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):
        yield


class TestRideRequest:
    """Test class for ride request functionality."""
    
    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    @patch('app.services.ride_service._generate_coordinates_for_location')
    @patch('app.services.ride_service._calculate_ride_estimation')
    def test_create_ride_request_successful(self, mock_calc_estimation, mock_gen_coords, 
                                           mock_require_user, mock_uuid, mock_user_data):
        """Test that a ride request can be created successfully."""
        # Setup mocks
        mock_require_user.return_value = mock_user_data
        mock_gen_coords.side_effect = [(40.7128, -74.0060), (42.3601, -71.0589)]
        mock_calc_estimation.return_value = (10.5, 25, 35.75)  # distance, duration, fare
        
        # Mock location creation responses
        pickup_location_id = str(uuid.uuid4())
        dropoff_location_id = str(uuid.uuid4())
        ride_id = "12345678-1234-5678-1234-567812345678"
        
        pickup_location = {
            "id": pickup_location_id,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "address": TEST_PICKUP["address"],
            "city": TEST_PICKUP["city"],
            "state": TEST_PICKUP["state"],
            "postal_code": TEST_PICKUP["postal"],
            "country": TEST_PICKUP["country"],
            "user_id": TEST_USER_ID
        }
        
        dropoff_location = {
            "id": dropoff_location_id,
            "latitude": 42.3601,
            "longitude": -71.0589,
            "address": TEST_DROPOFF["address"],
            "city": TEST_DROPOFF["city"],
            "state": TEST_DROPOFF["state"],
            "postal_code": TEST_DROPOFF["postal"],
            "country": TEST_DROPOFF["country"],
            "user_id": TEST_USER_ID
        }
        
        # Mock the API responses
        # 1. POST to create pickup location
        responses.add(
            responses.POST,
            f"{TEST_BASE_URL}/locations",
            json=pickup_location,
            status=201
        )
        
        # 2. POST to create dropoff location
        responses.add(
            responses.POST,
            f"{TEST_BASE_URL}/locations",
            json=dropoff_location,
            status=201
        )
        
        # 3. POST to create the ride
        expected_ride = {
            "id": ride_id,
            "user_id": TEST_USER_ID,
            "pickup_location_id": pickup_location_id,
            "dropoff_location_id": dropoff_location_id,
            "request_time": datetime.now().isoformat(),  # This will be different but we'll check presence
            "status": RideStatus.REQUESTED.name,
            "estimated_fare": 35.75,
            "distance": 10.5,
            "duration": 25,
            "driver_id": None,
            "start_time": None,
            "end_time": None,
            "actual_fare": None,
            "payment_id": None,
            "rating": None,
            "feedback": None,
            # Location details added after creation
            "pickup_location": pickup_location,
            "dropoff_location": dropoff_location
        }
        
        # Use a matcher for the request body to be more flexible with timestamps
        def ride_matcher(request):
            body = json.loads(request.body)
            # Check essential fields but be flexible with exact timestamp
            assert body['user_id'] == TEST_USER_ID
            assert body['pickup_location_id'] == pickup_location_id
            assert body['dropoff_location_id'] == dropoff_location_id
            assert body['status'] == RideStatus.REQUESTED.name
            assert 'request_time' in body
            assert body['estimated_fare'] == 35.75
            assert body['distance'] == 10.5
            assert body['duration'] == 25
            return True
            
        responses.add_callback(
            responses.POST,
            f"{TEST_BASE_URL}/rides",
            callback=lambda request: (201, {}, json.dumps({
                **expected_ride,
                "request_time": json.loads(request.body)["request_time"]  # Use the timestamp from the request
            })),
            content_type='application/json',
            match=[ride_matcher]
        )
        
        # Call the function being tested
        result = RideService.create_ride_request(
            TEST_TOKEN,
            TEST_PICKUP["address"],
            TEST_PICKUP["city"],
            TEST_PICKUP["state"],
            TEST_PICKUP["postal"],
            TEST_PICKUP["country"],
            TEST_DROPOFF["address"],
            TEST_DROPOFF["city"],
            TEST_DROPOFF["state"],
            TEST_DROPOFF["postal"],
            TEST_DROPOFF["country"]
        )
        
        # Assertions
        assert result["id"] == ride_id
        assert result["user_id"] == TEST_USER_ID
        assert result["status"] == RideStatus.REQUESTED.name
        assert result["pickup_location_id"] == pickup_location_id
        assert result["dropoff_location_id"] == dropoff_location_id
        assert "request_time" in result
        assert result["estimated_fare"] == 35.75
        assert result["distance"] == 10.5
        assert result["duration"] == 25
        assert result["driver_id"] is None
        
        # Verify location details are included
        assert "pickup_location" in result
        assert result["pickup_location"]["address"] == TEST_PICKUP["address"]
        
        assert "dropoff_location" in result
        assert result["dropoff_location"]["address"] == TEST_DROPOFF["address"]
        
        # Verify all mocks were called correctly
        mock_require_user.assert_called_once_with(TEST_TOKEN, ["passenger"])
        assert mock_gen_coords.call_count == 2
        mock_calc_estimation.assert_called_once_with(40.7128, -74.0060, 42.3601, -71.0589)

    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    def test_create_ride_request_unauthorized(self, mock_require_user):
        """Test that an unauthorized user cannot create a ride request."""
        # Setup mock to simulate authorization failure
        mock_require_user.side_effect = AuthError("Access denied. This action requires passenger user type")
        
        # Call the function and expect it to raise AuthError
        with pytest.raises(AuthError) as excinfo:
            RideService.create_ride_request(
                "invalid_token",
                TEST_PICKUP["address"],
                TEST_PICKUP["city"],
                TEST_PICKUP["state"],
                TEST_PICKUP["postal"],
                TEST_PICKUP["country"],
                TEST_DROPOFF["address"],
                TEST_DROPOFF["city"],
                TEST_DROPOFF["state"],
                TEST_DROPOFF["postal"],
                TEST_DROPOFF["country"]
            )
        
        # Verify the error message
        assert "Access denied" in str(excinfo.value)
        
    @responses.activate
    @patch('app.services.auth_service.AuthService.require_user_type')
    @patch('app.services.ride_service._generate_coordinates_for_location')
    def test_create_ride_request_api_error(self, mock_gen_coords, mock_require_user, mock_user_data):
        """Test handling of API error during ride request creation."""
        # Setup mocks
        mock_require_user.return_value = mock_user_data
        mock_gen_coords.return_value = (40.7128, -74.0060)  # Same coords for simplicity
        
        # Mock an API error response for location creation
        responses.add(
            responses.POST,
            f"{TEST_BASE_URL}/locations",
            json={"error": "Server error"},
            status=500
        )
        
        # Call the function and expect it to raise RideServiceError
        with pytest.raises(RideServiceError) as excinfo:
            RideService.create_ride_request(
                TEST_TOKEN,
                TEST_PICKUP["address"],
                TEST_PICKUP["city"],
                TEST_PICKUP["state"],
                TEST_PICKUP["postal"],
                TEST_PICKUP["country"],
                TEST_DROPOFF["address"],
                TEST_DROPOFF["city"],
                TEST_DROPOFF["state"],
                TEST_DROPOFF["postal"],
                TEST_DROPOFF["country"]
            )
        
        # Verify the error message
        assert "Ride request creation failed" in str(excinfo.value)