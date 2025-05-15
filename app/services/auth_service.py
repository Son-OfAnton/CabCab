"""Authentication service for CabCab application."""

import os
import json
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import requests
from uuid import UUID, uuid4
from enum import Enum
import logging
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for our custom JSON server
BASE_URL = "http://localhost:3000"

# Secret for JWT token generation - in production, move to env variables
JWT_SECRET = os.getenv("JWT_SECRET", "cabcab_secret_key")
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
        if not hashed_password:
            return False
        
        try:
            plain_password_bytes = plain_password.encode('utf-8')
            hashed_password_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False
    
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
            
            # Hash the password
            hashed_password = AuthService._hash_password(password)
            
            # Create the new passenger
            user_id = str(uuid4())
            new_user = {
                "id": user_id,
                "email": email,
                "password": hashed_password,  # Store the hashed password
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
            
            # Log user creation for debugging
            logger.info(f"Creating new passenger user: {email}")
            logger.info(f"Password field is present: {'password' in new_user}")
            
            # Save the user to the database
            response = requests.post(f"{BASE_URL}/users", json=new_user)
            response.raise_for_status()
            
            # Verify the user was saved with password
            created_user = response.json()
            if 'password' not in created_user:
                logger.warning(f"Password field missing from response for user {email}")
                
                # Additional verification - check if the user exists with the password
                try:
                    check_response = requests.get(f"{BASE_URL}/users/{user_id}")
                    if check_response.status_code == 200:
                        saved_user = check_response.json()
                        if 'password' not in saved_user:
                            logger.error("Password field missing from saved user!")
                            
                            # Attempt to update the user to add the password
                            update_user = saved_user.copy()
                            update_user['password'] = hashed_password
                            update_response = requests.put(f"{BASE_URL}/users/{user_id}", json=update_user)
                            if update_response.status_code == 200:
                                logger.info("Successfully added password to user record")
                            else:
                                logger.error(f"Failed to update user with password: {update_response.status_code}")
                except Exception as e:
                    logger.error(f"Error checking/updating user: {str(e)}")
            
            # Remove password before returning
            user_data = created_user.copy()
            if "password" in user_data:
                del user_data["password"]
            
            # Generate token
            token = AuthService._generate_jwt(user_id, UserType.PASSENGER.value)
            
            return {
                "user": user_data,
                "token": token,
                "temp_password": hashed_password  # For signin workaround
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
            
            # Hash the password
            hashed_password = AuthService._hash_password(password)
            
            # Create the new driver
            user_id = str(uuid4())
            new_user = {
                "id": user_id,
                "email": email,
                "password": hashed_password,  # Store the hashed password
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
            
            # Log user creation for debugging
            logger.info(f"Creating new driver user: {email}")
            logger.info(f"Password field is present: {'password' in new_user}")
            
            # Save the user to the database
            response = requests.post(f"{BASE_URL}/users", json=new_user)
            response.raise_for_status()
            
            # Get the created user from the response
            created_user = response.json()
            
            # Check if password was saved
            if 'password' not in created_user:
                logger.warning(f"Password field missing from response for user {email}")
                
                # Store password in a separate passwords collection as a workaround
                password_data = {
                    "user_id": user_id,
                    "email": email,
                    "hashed_password": hashed_password
                }
                try:
                    # Create passwords collection if it doesn't exist
                    passwords_response = requests.get(f"{BASE_URL}/passwords")
                    if passwords_response.status_code == 404:
                        # Initialize passwords collection
                        init_db_response = requests.get(f"{BASE_URL}/")
                        if init_db_response.status_code == 200:
                            db = init_db_response.json()
                            if 'passwords' not in db:
                                db['passwords'] = []
                                requests.put(f"{BASE_URL}/", json=db)
                    
                    # Save password data
                    pass_response = requests.post(f"{BASE_URL}/passwords", json=password_data)
                    if pass_response.status_code == 201:
                        logger.info(f"Saved password for user {email} in separate collection")
                except Exception as e:
                    logger.error(f"Failed to save password in separate collection: {str(e)}")
                
                # Also try to update the user record with the password
                try:
                    update_user = created_user.copy() 
                    update_user['password'] = hashed_password
                    update_response = requests.put(f"{BASE_URL}/users/{user_id}", json=update_user)
                    if update_response.status_code == 200:
                        logger.info("Successfully added password to user record")
                    else:
                        logger.error(f"Failed to update user with password: {update_response.status_code}")
                except Exception as e:
                    logger.error(f"Error updating user password: {str(e)}")
            
            # Remove password before returning
            user_data = created_user.copy()
            if "password" in user_data:
                del user_data["password"]
            
            # Generate token
            token = AuthService._generate_jwt(user_id, UserType.DRIVER.value)
            
            return {
                "user": user_data,
                "token": token,
                "temp_password": hashed_password  # For signin workaround
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

        # Check if user is banned

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
            user_id = user.get('id')
            
            if user.get('user_type') == UserType.PASSENGER.value and user.get('is_banned', False):
                reason = user.get('ban_reason') or "No reason provided"
                ban_type = "permanently" if user.get('is_permanent_ban', False) else "temporarily"
                raise AuthError(f"Your account has been {ban_type} banned. Reason: {reason}. Please contact customer support for assistance.")
            
            # Check if password is missing in the user record
            if 'password' not in user or not user.get('password'):
                logger.warning(f"Password field missing for user {email}, looking in passwords collection")
                
                # Try to get password from passwords collection
                try:
                    pass_response = requests.get(f"{BASE_URL}/passwords/query?email={email}")
                    if pass_response.status_code == 200:
                        passwords = pass_response.json()
                        if passwords:
                            password_record = passwords[0]
                            hashed_password = password_record.get('hashed_password')
                            if hashed_password:
                                # Verify password using the stored hash
                                if AuthService._verify_password(password, hashed_password):
                                    logger.info(f"Password verified from passwords collection for {email}")
                                    # Add the password to the user object
                                    user['password'] = hashed_password
                                    
                                    # Also try to update the user in the database
                                    try:
                                        update_user = user.copy()
                                        update_response = requests.put(f"{BASE_URL}/users/{user_id}", json=update_user)
                                        if update_response.status_code == 200:
                                            logger.info(f"Updated user record with password for {email}")
                                    except Exception as e:
                                        logger.error(f"Failed to update user record: {str(e)}")
                                else:
                                    raise AuthError("Invalid password")
                except Exception as e:
                    logger.error(f"Error checking passwords collection: {str(e)}")
                    raise AuthError("Invalid credentials")
            
            # If we still don't have a valid password field, authentication fails
            if 'password' not in user or not user.get('password'):
                raise AuthError("Account data is missing password information. Please register again or contact support.")
            
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
            
        except AuthError:
            # Re-raise auth errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
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

            if user.get('is_banned', False) and user.get('user_type') == UserType.PASSENGER.value:
                reason = user.get('ban_reason') or "No reason provided"
                raise AuthError(f"Your account is banned: {reason}")
            
            # Remove password before returning
            if "password" in user:
                del user['password']
            
            return user
            
        except requests.RequestException as e:
            raise AuthError(f"Token verification failed: {str(e)}")
    
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
    
from typing import Dict, Any, Optional

from app.services.auth_service import AuthService, AuthError
from app.services.user_service import UserService, UserServiceError


class AuthValidationError(Exception):
    """Custom exception for authentication validation errors."""
    pass


def validate_user_not_banned(token: str) -> Dict[str, Any]:
    """
    Validate that a user is not banned.
    
    Args:
        token: JWT token for authentication
        
    Returns:
        Dict: User data if not banned
        
    Raises:
        AuthValidationError: If user is banned
        AuthError: If token is invalid
    """
    try:
        # First verify the token and get user data
        user = AuthService.verify_token(token)
        
        # Admin users are never subject to bans
        if user.get('user_type') == 'admin':
            return user
            
        # Check if user is banned
        try:
            ban_status = UserService.get_ban_status(user['id'])
            
            if ban_status.get('is_banned'):
                reason = ban_status.get('reason') or "No reason provided"
                permanent = "permanently" if ban_status.get('is_permanent') else "temporarily"
                
                raise AuthValidationError(
                    f"Your account has been {permanent} banned. Reason: {reason}. "
                    f"Please contact customer support for assistance."
                )
        except UserServiceError:
            # If checking ban status fails, allow operation to continue
            pass
            
        return user
            
    except AuthError as e:
        raise  # Re-throw auth errors without wrapping