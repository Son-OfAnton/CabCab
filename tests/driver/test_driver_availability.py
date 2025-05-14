"""Tests for driver availability toggling feature in CabCab."""

import pytest
import json
import responses
from unittest.mock import patch, MagicMock
from app.services.auth_service import AuthService, AuthError, UserType


# Constants for testing
TEST_BASE_URL = "http://localhost:3000"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZHJpdmVyLTEyMzQ1IiwidXNlcl90eXBlIjoiZHJpdmVyIiwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjE2MDAwMDAwMDB9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
TEST_DRIVER_ID = "driver-12345"


@pytest.fixture
def mock_driver_data():
    """Fixture for sample driver data."""
    return {
        "id": TEST_DRIVER_ID,
        "email": "driver@example.com",
        "first_name": "Test",
        "last_name": "Driver",
        "phone": "1234567890",
        "user_type": "driver",
        "license_number": "DL123456",
        "is_verified": True,
        "is_available": False,  # Initially not available
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
        "is_verified": False,  # Not verified yet
        "is_available": False,
        "rating": None,
        "rating_count": 0,
        "vehicle_id": "vehicle-789",
        "created_at": "2023-01-01T12:00:00",
        "updated_at": "2023-01-01T12:00:00"
    }


@pytest.fixture
def mock_non_driver_data():
    """Fixture for a non-driver user."""
    return {
        "id": "user-67890",
        "email": "passenger@example.com",
        "first_name": "Test",
        "last_name": "Passenger",
        "phone": "9876543210",
        "user_type": "passenger",
        "created_at": "2023-01-01T12:00:00",
        "updated_at": "2023-01-01T12:00:00"
    }


class TestDriverAvailability:
    """Test class for driver availability toggling functionality."""

    @responses.activate
    @patch('app.services.auth_service.AuthService._verify_jwt')
    def test_set_driver_available(self, mock_verify_jwt, mock_driver_data):
        """Test successfully setting a driver as available."""
        # Set up JWT verification mock
        mock_verify_jwt.return_value = {
            "user_id": TEST_DRIVER_ID,
            "user_type": "driver"
        }

        # Mock the GET request to retrieve current driver data
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            json=mock_driver_data,
            status=200
        )

        # Create the expected data after update
        expected_updated_data = mock_driver_data.copy()
        expected_updated_data["is_available"] = True
        expected_updated_data["updated_at"] = "2023-01-01T12:30:00"  # New timestamp

        # Mock the PUT request to update driver availability
        def request_callback(request):
            payload = json.loads(request.body)
            # Verify is_available was set to True
            assert payload["is_available"] is True
            # Return status code, headers, and body
            return (200, {}, json.dumps(expected_updated_data))

        responses.add_callback(
            responses.PUT,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            callback=request_callback,
            content_type="application/json"
        )

        # Call the function being tested
        result = AuthService.set_driver_availability(TEST_TOKEN, True)

        # Assertions
        assert result["is_available"] is True
        assert result["id"] == TEST_DRIVER_ID
        assert mock_verify_jwt.call_count == 1
        assert len(responses.calls) == 2  # One GET and one PUT

    @responses.activate
    @patch('app.services.auth_service.AuthService._verify_jwt')
    def test_set_driver_unavailable(self, mock_verify_jwt, mock_driver_data):
        """Test successfully setting a driver as unavailable."""
        # Set up JWT verification mock
        mock_verify_jwt.return_value = {
            "user_id": TEST_DRIVER_ID,
            "user_type": "driver"
        }

        # Modify fixture to set driver as initially available
        available_driver = mock_driver_data.copy()
        available_driver["is_available"] = True

        # Mock the GET request to retrieve current driver data
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            json=available_driver,
            status=200
        )

        # Create the expected data after update
        expected_updated_data = available_driver.copy()
        expected_updated_data["is_available"] = False
        expected_updated_data["updated_at"] = "2023-01-01T12:30:00"  # New timestamp

        # Mock the PUT request to update driver availability
        def request_callback(request):
            payload = json.loads(request.body)
            # Verify is_available was set to False
            assert payload["is_available"] is False
            # Return status code, headers, and body
            return (200, {}, json.dumps(expected_updated_data))

        responses.add_callback(
            responses.PUT,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            callback=request_callback,
            content_type="application/json"
        )

        # Call the function being tested
        result = AuthService.set_driver_availability(TEST_TOKEN, False)

        # Assertions
        assert result["is_available"] is False
        assert result["id"] == TEST_DRIVER_ID
        assert mock_verify_jwt.call_count == 1
        assert len(responses.calls) == 2  # One GET and one PUT

    @responses.activate
    @patch('app.services.auth_service.AuthService._verify_jwt')
    def test_set_availability_unverified_driver(self, mock_verify_jwt, mock_unverified_driver_data):
        """Test setting availability for an unverified driver."""
        # Set up JWT verification mock
        mock_verify_jwt.return_value = {
            "user_id": TEST_DRIVER_ID,
            "user_type": "driver"
        }

        # Mock the responses for the require_user_type method
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            json=mock_unverified_driver_data,
            status=200
        )

        # The test should allow unverified drivers to set availability
        # as verification is only checked when accepting rides
        
        # Create the expected data after update
        expected_updated_data = mock_unverified_driver_data.copy()
        expected_updated_data["is_available"] = True
        expected_updated_data["updated_at"] = "2023-01-01T12:30:00"  # New timestamp

        # Mock the PUT request to update driver availability
        responses.add(
            responses.PUT,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            json=expected_updated_data,
            status=200
        )

        # Call the function being tested
        result = AuthService.set_driver_availability(TEST_TOKEN, True)

        # Assertions
        assert result["is_available"] is True
        assert result["is_verified"] is False  # Still not verified
        assert result["id"] == TEST_DRIVER_ID
        assert mock_verify_jwt.call_count == 1
        assert len(responses.calls) == 2  # One GET and one PUT

    @responses.activate
    @patch('app.services.auth_service.AuthService._verify_jwt')
    def test_set_availability_non_driver(self, mock_verify_jwt, mock_non_driver_data):
        """Test setting availability for a non-driver user."""
        # Set up JWT verification mock
        mock_verify_jwt.return_value = {
            "user_id": "user-67890",
            "user_type": "passenger"
        }

        # Mock the responses for the require_user_type method
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/user-67890",
            json=mock_non_driver_data,
            status=200
        )

        # Call the function and expect it to raise AuthError
        with pytest.raises(AuthError) as excinfo:
            AuthService.set_driver_availability(TEST_TOKEN, True)

        # Verify the error message
        assert "Access denied" in str(excinfo.value)
        assert mock_verify_jwt.call_count == 1
        assert len(responses.calls) == 1  # Only one GET for user data

    @responses.activate
    def test_set_availability_invalid_token(self):
        """Test setting availability with an invalid token."""
        # No mock setup for _verify_jwt means it will use the real implementation
        # which will fail for our fake token

        # Mock the JWT verification to fail
        with patch('app.services.auth_service.AuthService._verify_jwt') as mock_verify:
            mock_verify.side_effect = AuthError("Invalid token")

            # Call the function and expect it to raise AuthError
            with pytest.raises(AuthError) as excinfo:
                AuthService.set_driver_availability("invalid_token", True)

            # Verify the error message
            assert "Invalid token" in str(excinfo.value)
            assert mock_verify.call_count == 1
            assert len(responses.calls) == 0  # No API calls made

    @responses.activate
    @patch('app.services.auth_service.AuthService._verify_jwt')
    def test_set_availability_server_error(self, mock_verify_jwt, mock_driver_data):
        """Test handling server errors when setting availability."""
        # Set up JWT verification mock
        mock_verify_jwt.return_value = {
            "user_id": TEST_DRIVER_ID,
            "user_type": "driver"
        }

        # Mock the GET request to retrieve current driver data
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            json=mock_driver_data,
            status=200
        )

        # Mock server error for the PUT request
        responses.add(
            responses.PUT,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            json={"error": "Internal server error"},
            status=500
        )

        # Call the function and expect it to raise AuthError
        with pytest.raises(AuthError) as excinfo:
            AuthService.set_driver_availability(TEST_TOKEN, True)

        # Verify the error message
        assert "Profile update failed" in str(excinfo.value)
        assert mock_verify_jwt.call_count == 1
        assert len(responses.calls) == 2  # One GET and one failed PUT

    @responses.activate
    @patch('app.services.auth_service.AuthService._verify_jwt')
    def test_set_availability_user_not_found(self, mock_verify_jwt):
        """Test setting availability when user is not found."""
        # Set up JWT verification mock
        mock_verify_jwt.return_value = {
            "user_id": TEST_DRIVER_ID,
            "user_type": "driver"
        }

        # Mock 404 response for user not found
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/{TEST_DRIVER_ID}",
            json={"error": "User not found"},
            status=404
        )

        # Call the function and expect it to raise AuthError
        with pytest.raises(AuthError) as excinfo:
            AuthService.set_driver_availability(TEST_TOKEN, True)

        # Verify the error message
        assert "not found" in str(excinfo.value)
        assert mock_verify_jwt.call_count == 1
        assert len(responses.calls) == 1  # Only one failed GET