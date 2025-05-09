"""Authentication service for CabCab application."""

import os
import json
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import requests
from uuid import uuid4
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

# Base URL for our custom JSON server
BASE_URL = "http://localhost:3000"

# Secret for JWT token generation - in production, move to env variables
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


# User types
class UserType(Enum):
    """Types of users in the system."""
    PASSENGER = "passenger"
    DRIVER = "driver"
    ADMIN = "admin"


class AuthError(Exception):
    """Custom exception for authentication errors."""
    pass


class AuthService:
    """Service for handling user authentication."""

    @staticmethod
    def _hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Previously hashed password
            
        Returns:
            bool: True if password matches, False otherwise
        """
        plain_password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    
    @staticmethod
    def _generate_jwt(user_id: str, user_type: str) -> str:
        """
        Generate a JWT token for a user.
        
        Args:
            user_id: User ID to encode in the token
            user_type: Type of user (passenger, driver, admin)
            
        Returns:
            str: JWT token
        """
        payload = {
            "user_id": user_id,
            "user_type": user_type,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def _verify_jwt(token: str) -> Dict[str, Any]:
        """
        Verify a JWT token and return its payload.
        
        Args:
            token: JWT token
            
        Returns:
            Dict: Token payload
            
        Raises:
            AuthError: If token is invalid or expired
        """
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.PyJWTError as e:
            raise AuthError(f"Invalid token: {str(e)}")
    
    @staticmethod
    def register_passenger(email: str, password: str, first_name: str, last_name: str, phone: str) -> Dict[str, Any]:
        """
        Register a new passenger.
        
        Args:
            email: User's email
            password: User's password
            first_name: User's first name
            last_name: User's last name
            phone: User's phone number
            
        Returns:
            Dict: User data with token
            
        Raises:
            AuthError: If registration fails
        """
        try:
            # Check if user already exists
            response = requests.get(f"{BASE_URL}/users/query?email={email}")
            
            if response.status_code == 404:
                # Collection not found, this is the first user
                existing_users = []
            else:
                response.raise_for_status()
                existing_users = response.json()
            
            if existing_users:
                raise AuthError(f"User with email {email} already exists")
            
            # Create the new passenger
            user_id = str(uuid4())
            new_user = {
                "id": user_id,
                "email": email,
                "password": AuthService._hash_password(password),
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "user_type": UserType.PASSENGER.value,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_active": True,
                "payment_methods": [],
                "rating": None
            }
            
            # Save the user to the database
            response = requests.post(f"{BASE_URL}/users", json=new_user)
            response.raise_for_status()
            
            # Remove password before returning
            user_data = response.json()
            if "password" in user_data:
                del user_data["password"]
            
            # Generate token
            token = AuthService._generate_jwt(user_id, UserType.PASSENGER.value)
            
            return {
                "user": user_data,
                "token": token
            }
            
        except requests.RequestException as e:
            raise AuthError(f"Registration failed: {str(e)}")
    
    @staticmethod
    def register_driver(email: str, password: str, first_name: str, last_name: str, 
                        phone: str, license_number: str) -> Dict[str, Any]:
        """
        Register a new driver.
        
        Args:
            email: Driver's email
            password: Driver's password
            first_name: Driver's first name
            last_name: Driver's last name
            phone: Driver's phone number
            license_number: Driver's license number
            
        Returns:
            Dict: User data with token
            
        Raises:
            AuthError: If registration fails
        """
        try:
            # Check if user already exists
            response = requests.get(f"{BASE_URL}/users/query?email={email}")
            
            if response.status_code == 404:
                # Collection not found, this is the first user
                existing_users = []
            else:
                response.raise_for_status()
                existing_users = response.json()
            
            if existing_users:
                raise AuthError(f"User with email {email} already exists")
            
            # Create the new driver
            user_id = str(uuid4())
            new_user = {
                "id": user_id,
                "email": email,
                "password": AuthService._hash_password(password),
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "user_type": UserType.DRIVER.value,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_active": True,
                "license_number": license_number,
                "is_verified": False,  # Drivers need to be verified
                "is_available": False,
                "vehicle_id": None,
                "rating": None
            }
            
            # Save the user to the database
            response = requests.post(f"{BASE_URL}/users", json=new_user)
            response.raise_for_status()
            
            # Remove password before returning
            user_data = response.json()
            if "password" in user_data:
                del user_data["password"]
            
            # Generate token
            token = AuthService._generate_jwt(user_id, UserType.DRIVER.value)
            
            return {
                "user": user_data,
                "token": token
            }
            
        except requests.RequestException as e:
            raise AuthError(f"Registration failed: {str(e)}")
    
    @staticmethod
    def register_admin(email: str, password: str, first_name: str, last_name: str, 
                       phone: str, admin_code: str) -> Dict[str, Any]:
        """
        Register a new admin.
        
        Args:
            email: Admin's email
            password: Admin's password
            first_name: Admin's first name
            last_name: Admin's last name
            phone: Admin's phone number
            admin_code: Admin registration code for validation
            
        Returns:
            Dict: User data with token
            
        Raises:
            AuthError: If registration fails
        """
        # In a real application, this would validate against a secure admin code
        # For demo purposes, we're using a simple hardcoded value
        ADMIN_REGISTRATION_CODE = "admin123"
        
        if admin_code != ADMIN_REGISTRATION_CODE:
            raise AuthError("Invalid admin registration code")
        
        try:
            # Check if user already exists
            response = requests.get(f"{BASE_URL}/users/query?email={email}")
            
            if response.status_code == 404:
                # Collection not found, this is the first user
                existing_users = []
            else:
                response.raise_for_status()
                existing_users = response.json()
            
            if existing_users:
                raise AuthError(f"User with email {email} already exists")
            
            # Create the new admin
            user_id = str(uuid4())
            new_user = {
                "id": user_id,
                "email": email,
                "password": AuthService._hash_password(password),
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "user_type": UserType.ADMIN.value,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_active": True
            }
            
            # Save the user to the database
            response = requests.post(f"{BASE_URL}/users", json=new_user)
            response.raise_for_status()
            
            # Remove password before returning
            user_data = response.json()
            if "password" in user_data:
                del user_data["password"]
            
            # Generate token
            token = AuthService._generate_jwt(user_id, UserType.ADMIN.value)
            
            return {
                "user": user_data,
                "token": token
            }
            
        except requests.RequestException as e:
            raise AuthError(f"Registration failed: {str(e)}")
    
    @staticmethod
    def login(email: str, password: str) -> Dict[str, Any]:
        """
        Login a user.
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            Dict: User data with token
            
        Raises:
            AuthError: If login fails
        """
        try:
            # Find the user
            response = requests.get(f"{BASE_URL}/users/query?email={email}")
            
            if response.status_code == 404:
                # Collection not found
                raise AuthError(f"No user found with email {email}")
            
            response.raise_for_status()
            users = response.json()
            
            if not users:
                raise AuthError(f"No user found with email {email}")
            
            user = users[0]
            
            # Verify the password
            if not AuthService._verify_password(password, user['password']):
                raise AuthError("Invalid password")
            
            # Generate token
            token = AuthService._generate_jwt(user['id'], user['user_type'])
            
            # Remove password before returning
            del user['password']
            
            return {
                "user": user,
                "token": token
            }
            
        except requests.RequestException as e:
            raise AuthError(f"Login failed: {str(e)}")
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Verify a token and return the associated user.
        
        Args:
            token: JWT token
            
        Returns:
            Dict: User data
            
        Raises:
            AuthError: If token verification fails
        """
        try:
            # Decode the token
            payload = AuthService._verify_jwt(token)
            user_id = payload.get('user_id')
            
            if not user_id:
                raise AuthError("Invalid token payload")
            
            # Get the user from the database
            response = requests.get(f"{BASE_URL}/users/{user_id}")
            
            if response.status_code == 404:
                raise AuthError(f"User with ID {user_id} not found")
                
            response.raise_for_status()
            user = response.json()
            
            # Remove password before returning
            if "password" in user:
                del user['password']
            
            return user
            
        except requests.RequestException as e:
            raise AuthError(f"Token verification failed: {str(e)}")
    
    @staticmethod
    def update_profile(token: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a user's profile.
        
        Args:
            token: JWT token for authentication
            update_data: Dictionary containing fields to update
            
        Returns:
            Dict: Updated user data
            
        Raises:
            AuthError: If profile update fails
        """
        try:
            # Get the current user from the token
            payload = AuthService._verify_jwt(token)
            user_id = payload.get('user_id')
            user_type = payload.get('user_type')
            
            if not user_id:
                raise AuthError("Invalid token payload")
            
            # Get the current user data
            response = requests.get(f"{BASE_URL}/users/{user_id}")
            
            if response.status_code == 404:
                raise AuthError(f"User with ID {user_id} not found")
                
            response.raise_for_status()
            current_user = response.json()
            
            # Fields that cannot be updated
            protected_fields = ['id', 'email', 'password', 'created_at', 'user_type']
            
            # Fields specific to user types
            ptype_field_restrictions = {
                UserType.PASSENGER.value: ['license_number', 'is_verified', 'is_available', 'vehicle_id'],
                UserType.DRIVER.value: ['payment_methods'],
                UserType.ADMIN.value: ['payment_methods', 'license_number', 'is_verified', 'is_available', 'vehicle_id']
            }
            
            # Add type-specific protected fields
            if user_type in ptype_field_restrictions:
                protected_fields.extend(ptype_field_restrictions[user_type])
            
            # Create updated user data
            updated_user = current_user.copy()
            
            # Update allowed fields
            for key, value in update_data.items():
                if key not in protected_fields and value is not None:
                    updated_user[key] = value
            
            # Update timestamp
            updated_user['updated_at'] = datetime.now().isoformat()
            
            # Save the updated user
            response = requests.put(f"{BASE_URL}/users/{user_id}", json=updated_user)
            response.raise_for_status()
            updated_user_data = response.json()
            
            # Remove password before returning
            if "password" in updated_user_data:
                del updated_user_data["password"]
            
            return updated_user_data
            
        except requests.RequestException as e:
            raise AuthError(f"Profile update failed: {str(e)}")
    
    @staticmethod
    def change_password(token: str, current_password: str, new_password: str) -> Dict[str, Any]:
        """
        Change a user's password.
        
        Args:
            token: JWT token for authentication
            current_password: Current password for verification
            new_password: New password to set
            
        Returns:
            Dict: Updated user data
            
        Raises:
            AuthError: If password change fails
        """
        try:
            # Get the current user from the token
            payload = AuthService._verify_jwt(token)
            user_id = payload.get('user_id')
            
            if not user_id:
                raise AuthError("Invalid token payload")
            
            # Get the current user data
            response = requests.get(f"{BASE_URL}/users/{user_id}")
            
            if response.status_code == 404:
                raise AuthError(f"User with ID {user_id} not found")
                
            response.raise_for_status()
            current_user = response.json()
            
            # Verify the current password
            if not AuthService._verify_password(current_password, current_user['password']):
                raise AuthError("Current password is incorrect")
            
            # Create updated user data
            updated_user = current_user.copy()
            updated_user['password'] = AuthService._hash_password(new_password)
            updated_user['updated_at'] = datetime.now().isoformat()
            
            # Save the updated user
            response = requests.put(f"{BASE_URL}/users/{user_id}", json=updated_user)
            response.raise_for_status()
            updated_user_data = response.json()
            
            # Remove password before returning
            if "password" in updated_user_data:
                del updated_user_data["password"]
            
            return updated_user_data
            
        except requests.RequestException as e:
            raise AuthError(f"Password change failed: {str(e)}")
            
    @staticmethod
    def require_user_type(token: str, required_types: List[str]) -> Dict[str, Any]:
        """
        Verify that a user has one of the required types.
        
        Args:
            token: JWT token for authentication
            required_types: List of allowed user types
            
        Returns:
            Dict: User data if authorized
            
        Raises:
            AuthError: If user is not of the required type
        """
        # Verify the token and get the user
        payload = AuthService._verify_jwt(token)
        user_type = payload.get('user_type')
        
        if user_type not in required_types:
            allowed_types = ", ".join(required_types)
            raise AuthError(f"Access denied. This action requires one of these user types: {allowed_types}")
        
        return AuthService.verify_token(token)
    
    @staticmethod
    def set_driver_availability(token: str, is_available: bool) -> Dict[str, Any]:
        """
        Set a driver's availability status.
        
        Args:
            token: JWT token for authentication
            is_available: Whether the driver is available for rides
            
        Returns:
            Dict: Updated driver data
            
        Raises:
            AuthError: If not a driver or update fails
        """
        try:
            # Ensure user is a driver
            user = AuthService.require_user_type(token, [UserType.DRIVER.value])
            
            # Update availability status
            update_data = {'is_available': is_available}
            return AuthService.update_profile(token, update_data)
            
        except AuthError as e:
            raise e