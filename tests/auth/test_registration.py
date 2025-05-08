"""Unit tests for user registration functionality."""

import unittest
from unittest.mock import patch, MagicMock
import json
import jwt
from datetime import datetime

from app.auth.auth_service import AuthService, AuthError, UserType


class TestUserRegistration(unittest.TestCase):
    """Test cases for user registration functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_uuid = "test-uuid-123"
        self.test_email = "test@example.com"
        self.test_password = "password123"
        self.test_first_name = "Test"
        self.test_last_name = "User"
        self.test_phone = "555-123-4567"
        self.test_license = "DL123456789"
        self.admin_code = "admin123"
        self.hashed_password = "hashed_password_123"
        self.test_token = "test_jwt_token"
        
        # Common response for user creation
        self.user_response = MagicMock()
        self.user_response.status_code = 201
        self.user_response.json.return_value = {
            "id": self.mock_uuid,
            "email": self.test_email,
            "password": self.hashed_password,
            "first_name": self.test_first_name,
            "last_name": self.test_last_name,
            "phone": self.test_phone,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True
        }
    
    @patch('requests.get')
    @patch('requests.post')
    @patch('uuid.uuid4')
    @patch('app.auth.auth_service.AuthService._hash_password')
    @patch('app.auth.auth_service.AuthService._generate_jwt')
    def test_register_passenger(self, mock_generate_jwt, mock_hash_password, mock_uuid4, mock_post, mock_get):
        """Test successful passenger registration."""
        # Set up mocks
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=[]))
        mock_post.return_value = self.user_response
        mock_uuid4.return_value = self.mock_uuid
        mock_hash_password.return_value = self.hashed_password
        mock_generate_jwt.return_value = self.test_token
        
        # Add passenger-specific fields to response
        user_data = self.user_response.json()
        user_data["user_type"] = UserType.PASSENGER.value
        user_data["payment_methods"] = []
        user_data["rating"] = None
        
        # Call the method
        result = AuthService.register_passenger(
            self.test_email, self.test_password, self.test_first_name, self.test_last_name, self.test_phone
        )
        
        # Assertions
        mock_get.assert_called_once()
        mock_post.assert_called_once()
        mock_hash_password.assert_called_once_with(self.test_password)
        mock_generate_jwt.assert_called_once_with(self.mock_uuid, UserType.PASSENGER.value)
        
        self.assertIn("user", result)
        self.assertIn("token", result)
        self.assertEqual(result["token"], self.test_token)
        self.assertNotIn("password", result["user"])

    @patch('requests.get')
    @patch('requests.post')
    @patch('uuid.uuid4')
    @patch('app.auth.auth_service.AuthService._hash_password')
    @patch('app.auth.auth_service.AuthService._generate_jwt')
    def test_register_driver(self, mock_generate_jwt, mock_hash_password, mock_uuid4, mock_post, mock_get):
        """Test successful driver registration."""
        # Set up mocks
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=[]))
        mock_post.return_value = self.user_response
        mock_uuid4.return_value = self.mock_uuid
        mock_hash_password.return_value = self.hashed_password
        mock_generate_jwt.return_value = self.test_token
        
        # Add driver-specific fields to response
        user_data = self.user_response.json()
        user_data["user_type"] = UserType.DRIVER.value
        user_data["license_number"] = self.test_license
        user_data["is_verified"] = False
        user_data["is_available"] = False
        user_data["vehicle_id"] = None
        user_data["rating"] = None
        
        # Call the method
        result = AuthService.register_driver(
            self.test_email, self.test_password, self.test_first_name, 
            self.test_last_name, self.test_phone, self.test_license
        )
        
        # Assertions
        mock_get.assert_called_once()
        mock_post.assert_called_once()
        mock_hash_password.assert_called_once_with(self.test_password)
        mock_generate_jwt.assert_called_once_with(self.mock_uuid, UserType.DRIVER.value)
        
        # Verify the request payload contains driver-specific fields
        post_data = mock_post.call_args[1]['json']
        self.assertEqual(post_data["user_type"], UserType.DRIVER.value)
        self.assertEqual(post_data["license_number"], self.test_license)
        self.assertFalse(post_data["is_verified"])
        
        self.assertIn("user", result)
        self.assertIn("token", result)
        self.assertEqual(result["token"], self.test_token)
        self.assertNotIn("password", result["user"])

    @patch('requests.get')
    @patch('requests.post')
    @patch('uuid.uuid4')
    @patch('app.auth.auth_service.AuthService._hash_password')
    @patch('app.auth.auth_service.AuthService._generate_jwt')
    def test_register_admin(self, mock_generate_jwt, mock_hash_password, mock_uuid4, mock_post, mock_get):
        """Test successful admin registration with valid admin code."""
        # Set up mocks
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=[]))
        mock_post.return_value = self.user_response
        mock_uuid4.return_value = self.mock_uuid
        mock_hash_password.return_value = self.hashed_password
        mock_generate_jwt.return_value = self.test_token
        
        # Add admin-specific fields to response
        user_data = self.user_response.json()
        user_data["user_type"] = UserType.ADMIN.value
        
        # Call the method with valid admin code
        result = AuthService.register_admin(
            self.test_email, self.test_password, self.test_first_name, 
            self.test_last_name, self.test_phone, self.admin_code
        )
        
        # Assertions
        mock_get.assert_called_once()
        mock_post.assert_called_once()
        mock_hash_password.assert_called_once_with(self.test_password)
        mock_generate_jwt.assert_called_once_with(self.mock_uuid, UserType.ADMIN.value)
        
        # Verify the request payload contains admin-specific fields
        post_data = mock_post.call_args[1]['json']
        self.assertEqual(post_data["user_type"], UserType.ADMIN.value)
        
        self.assertIn("user", result)
        self.assertIn("token", result)
        self.assertEqual(result["token"], self.test_token)
        self.assertNotIn("password", result["user"])

    @patch('requests.get')
    def test_register_admin_invalid_code(self, mock_get):
        """Test admin registration with invalid admin code."""
        # Set up mock
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=[]))
        
        # Call the method with invalid admin code
        with self.assertRaises(AuthError) as context:
            AuthService.register_admin(
                self.test_email, self.test_password, self.test_first_name, 
                self.test_last_name, self.test_phone, "invalid_code"
            )
        
        # Verify the error message
        self.assertIn("Invalid admin registration code", str(context.exception))
        
        # Verify get was never called (validation fails before API call)
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_register_with_existing_email(self, mock_get):
        """Test registration with an email that already exists."""
        # Set up mock to return an existing user
        mock_get.return_value = MagicMock(
            status_code=200, 
            json=MagicMock(return_value=[{"email": self.test_email}])
        )
        
        # Try to register with the existing email
        with self.assertRaises(AuthError) as context:
            AuthService.register_passenger(
                self.test_email, self.test_password, self.test_first_name, 
                self.test_last_name, self.test_phone
            )
        
        # Verify the error message
        self.assertIn("already exists", str(context.exception))

    @patch('requests.get')
    def test_register_with_api_error(self, mock_get):
        """Test registration when the API returns an error."""
        # Set up mock to simulate API error
        mock_get.side_effect = Exception("API connection error")
        
        # Try to register
        with self.assertRaises(AuthError) as context:
            AuthService.register_passenger(
                self.test_email, self.test_password, self.test_first_name, 
                self.test_last_name, self.test_phone
            )
        
        # Verify the error message includes the API error
        self.assertIn("Registration failed", str(context.exception))
        self.assertIn("API connection error", str(context.exception))


if __name__ == "__main__":
    unittest.main()