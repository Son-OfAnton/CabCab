"""Unit tests for login and token functionality."""

import unittest
from unittest.mock import patch, MagicMock
import json
import jwt
from datetime import datetime, timedelta

from app.services.auth_service import AuthService, AuthError, UserType


class TestLoginAndToken(unittest.TestCase):
    """Test cases for login and token functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_user_id = "test-user-123"
        self.test_email = "test@example.com"
        self.test_password = "password123"
        self.hashed_password = "hashed_password_from_db"
        self.test_token = "test_jwt_token"
        
        # User data for testing
        self.user_data = {
            "id": self.test_user_id,
            "email": self.test_email,
            "password": self.hashed_password,
            "first_name": "Test",
            "last_name": "User",
            "phone": "555-123-4567",
            "user_type": UserType.PASSENGER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True,
            "payment_methods": []
        }
        
        # JWT secret and algorithm from AuthService
        self.jwt_secret = "cabcab_secret_key_change_in_production"
        self.jwt_algorithm = "HS256"
    
    @patch('requests.get')
    @patch('app.auth.auth_service.AuthService._verify_password')
    @patch('app.auth.auth_service.AuthService._generate_jwt')
    def test_login_success(self, mock_generate_jwt, mock_verify_password, mock_get):
        """Test successful login."""
        # Set up mocks
        mock_get.return_value = MagicMock(
            status_code=200, 
            json=MagicMock(return_value=[self.user_data])
        )
        mock_verify_password.return_value = True
        mock_generate_jwt.return_value = self.test_token
        
        # Call the method
        result = AuthService.login(self.test_email, self.test_password)
        
        # Assertions
        mock_get.assert_called_once()
        mock_verify_password.assert_called_once_with(self.test_password, self.hashed_password)
        mock_generate_jwt.assert_called_once_with(self.test_user_id, UserType.PASSENGER.value)
        
        self.assertIn("user", result)
        self.assertIn("token", result)
        self.assertEqual(result["token"], self.test_token)
        self.assertNotIn("password", result["user"])
        self.assertEqual(result["user"]["id"], self.test_user_id)
        self.assertEqual(result["user"]["email"], self.test_email)
    
    @patch('requests.get')
    def test_login_user_not_found(self, mock_get):
        """Test login with non-existent email."""
        # Set up mock to return empty list (no user found)
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=[]))
        
        # Try to login with non-existent email
        with self.assertRaises(AuthError) as context:
            AuthService.login("nonexistent@example.com", self.test_password)
        
        # Verify the error message
        self.assertIn("No user found with email", str(context.exception))
    
    @patch('requests.get')
    @patch('app.auth.auth_service.AuthService._verify_password')
    def test_login_invalid_password(self, mock_verify_password, mock_get):
        """Test login with invalid password."""
        # Set up mocks
        mock_get.return_value = MagicMock(
            status_code=200, 
            json=MagicMock(return_value=[self.user_data])
        )
        mock_verify_password.return_value = False
        
        # Try to login with invalid password
        with self.assertRaises(AuthError) as context:
            AuthService.login(self.test_email, "wrong_password")
        
        # Verify the error message
        self.assertIn("Invalid password", str(context.exception))
    
    def test_generate_and_verify_jwt(self):
        """Test JWT token generation and verification."""
        # Generate a token
        token = AuthService._generate_jwt(self.test_user_id, UserType.PASSENGER.value)
        
        # Verify the token
        payload = AuthService._verify_jwt(token)
        
        # Check payload contents
        self.assertEqual(payload["user_id"], self.test_user_id)
        self.assertEqual(payload["user_type"], UserType.PASSENGER.value)
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)
    
    def test_verify_jwt_expired_token(self):
        """Test verification of expired JWT token."""
        # Create an expired token
        payload = {
            "user_id": self.test_user_id,
            "user_type": UserType.PASSENGER.value,
            "exp": datetime.now(datetime.timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
            "iat": datetime.now(datetime.timezone.utc) - timedelta(hours=2)
        }
        expired_token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Try to verify expired token
        with self.assertRaises(AuthError) as context:
            AuthService._verify_jwt(expired_token)
        
        # Verify the error message
        self.assertIn("Invalid token", str(context.exception))
        self.assertIn("expired", str(context.exception).lower())
    
    @patch('requests.get')
    def test_verify_token(self, mock_get):
        """Test token verification with API call."""
        # Create JWT payload
        payload = {
            "user_id": self.test_user_id,
            "user_type": UserType.PASSENGER.value,
            "exp": datetime.now(datetime.timezone.utc) + timedelta(hours=24),
            "iat": datetime.now(datetime.timezone.utc)
        }
        valid_token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Set up mock for user retrieval
        user_data_without_password = self.user_data.copy()
        del user_data_without_password["password"]
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value=self.user_data)
        )
        
        # Call the method
        result = AuthService.verify_token(valid_token)
        
        # Assertions
        mock_get.assert_called_once_with(f"http://localhost:3000/users/{self.test_user_id}")
        self.assertEqual(result["id"], self.test_user_id)
        self.assertEqual(result["email"], self.test_email)
        self.assertNotIn("password", result)
    
    @patch('requests.get')
    def test_verify_token_user_not_found(self, mock_get):
        """Test token verification when user is not found."""
        # Create JWT payload
        payload = {
            "user_id": self.test_user_id,
            "user_type": UserType.PASSENGER.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        valid_token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Set up mock to simulate user not found
        mock_get.return_value = MagicMock(status_code=404)
        
        # Try to verify token for non-existent user
        with self.assertRaises(AuthError) as context:
            AuthService.verify_token(valid_token)
        
        # Verify the error message
        self.assertIn("User with ID", str(context.exception))
        self.assertIn("not found", str(context.exception))
    
    def test_require_user_type_authorized(self):
        """Test require_user_type when user is authorized."""
        # Create JWT payload with admin type
        payload = {
            "user_id": self.test_user_id,
            "user_type": UserType.ADMIN.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        admin_token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Mock verify_token to avoid API call
        with patch('app.auth.auth_service.AuthService.verify_token') as mock_verify:
            mock_verify.return_value = {"id": self.test_user_id, "user_type": UserType.ADMIN.value}
            
            # Call require_user_type with matching type
            result = AuthService.require_user_type(admin_token, [UserType.ADMIN.value])
            
            # Verify the call was successful
            mock_verify.assert_called_once_with(admin_token)
            self.assertEqual(result["id"], self.test_user_id)
    
    def test_require_user_type_unauthorized(self):
        """Test require_user_type when user is not authorized."""
        # Create JWT payload with passenger type
        payload = {
            "user_id": self.test_user_id,
            "user_type": UserType.PASSENGER.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        passenger_token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Mock verify_token to avoid API call
        with patch('app.auth.auth_service.AuthService.verify_token'):
            # Call require_user_type with non-matching type
            with self.assertRaises(AuthError) as context:
                AuthService.require_user_type(passenger_token, [UserType.ADMIN.value])
            
            # Verify the error message
            self.assertIn("Access denied", str(context.exception))
            self.assertIn(UserType.ADMIN.value, str(context.exception))


if __name__ == "__main__":
    unittest.main()