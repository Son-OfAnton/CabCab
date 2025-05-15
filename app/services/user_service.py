"""User management service for CabCab application."""

import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.services.auth_service import AuthService, AuthError, UserType

# Base URL for our custom JSON server
BASE_URL = "http://localhost:3000"


class UserServiceError(Exception):
    """Custom exception for user service errors."""
    pass


class UserService:
    """Service for handling user management operations."""
    
    @staticmethod
    def ban_passenger(token: str, user_email: str, reason: str = None, permanent: bool = False) -> Dict[str, Any]:
        """
        Ban a passenger from using the service.
        
        Args:
            token: JWT token for authentication (admin only)
            user_email: Email of the passenger to ban
            reason: Optional reason for the ban
            permanent: Whether the ban is permanent
            
        Returns:
            Dict: The banned passenger data
            
        Raises:
            UserServiceError: If banning the passenger fails
            AuthError: If authentication or authorization fails
        """
        try:
            # Verify token and ensure user is an admin
            admin_user = AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Find passenger by email
            response = requests.get(f"{BASE_URL}/users/query?email={user_email}")
            
            if response.status_code == 404 or not response.json():
                raise UserServiceError(f"User with email {user_email} not found")
                
            response.raise_for_status()
            passengers = response.json()
            
            # Find the first user with matching email
            passenger = next((p for p in passengers if p.get('email') == user_email), None)
            
            if not passenger:
                raise UserServiceError(f"User with email {user_email} not found")
                
            # Check if user is a passenger
            if passenger.get('user_type') != UserType.PASSENGER.value:
                raise UserServiceError(f"User with email {user_email} is not a passenger")
                
            # Check if already banned
            if passenger.get('is_banned', False):
                raise UserServiceError(f"Passenger {user_email} is already banned")
                
            # Update passenger with ban information
            passenger['is_banned'] = True
            passenger['ban_reason'] = reason
            passenger['is_permanent_ban'] = permanent
            passenger['banned_by'] = admin_user['id']
            passenger['banned_at'] = datetime.now().isoformat()
            passenger['updated_at'] = datetime.now().isoformat()
            
            # Save the updated passenger data
            response = requests.put(f"{BASE_URL}/users/{passenger['id']}", json=passenger)
            response.raise_for_status()
            
            # Create a ban record for audit purposes
            ban_record = {
                "id": f"ban_{datetime.now().timestamp()}",
                "user_id": passenger['id'],
                "user_email": user_email,
                "banned_by": admin_user['id'],
                "admin_email": admin_user['email'],
                "reason": reason,
                "is_permanent": permanent,
                "created_at": datetime.now().isoformat(),
                "active": True
            }
            
            # Save ban record in a 'bans' collection
            try:
                ban_response = requests.post(f"{BASE_URL}/bans", json=ban_record)
                ban_response.raise_for_status()
            except requests.RequestException as e:
                # If bans collection doesn't exist yet, it's not critical - continue
                pass
            
            return passenger
            
        except requests.RequestException as e:
            raise UserServiceError(f"Failed to ban passenger: {str(e)}")
        except AuthError as e:
            raise  # Re-throw auth errors without wrapping

    @staticmethod
    def unban_passenger(token: str, user_email: str) -> Dict[str, Any]:
        """
        Unban a previously banned passenger.
        
        Args:
            token: JWT token for authentication (admin only)
            user_email: Email of the passenger to unban
            
        Returns:
            Dict: The unbanned passenger data
            
        Raises:
            UserServiceError: If unbanning the passenger fails
            AuthError: If authentication or authorization fails
        """
        try:
            # Verify token and ensure user is an admin
            admin_user = AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Find passenger by email
            response = requests.get(f"{BASE_URL}/users/query?email={user_email}")
            
            if response.status_code == 404 or not response.json():
                raise UserServiceError(f"User with email {user_email} not found")
                
            response.raise_for_status()
            passengers = response.json()
            
            # Find the first user with matching email
            passenger = next((p for p in passengers if p.get('email') == user_email), None)
            
            if not passenger:
                raise UserServiceError(f"User with email {user_email} not found")
                
            # Check if user is a passenger
            if passenger.get('user_type') != UserType.PASSENGER.value:
                raise UserServiceError(f"User with email {user_email} is not a passenger")
                
            # Check if actually banned
            if not passenger.get('is_banned', False):
                raise UserServiceError(f"Passenger {user_email} is not currently banned")
                
            # Check if permanent ban
            if passenger.get('is_permanent_ban', False):
                # Additional check/confirmation might be needed for permanent bans
                pass
                
            # Update passenger to remove ban
            passenger['is_banned'] = False
            passenger['ban_reason'] = None
            passenger['is_permanent_ban'] = False
            passenger['unbanned_by'] = admin_user['id']
            passenger['unbanned_at'] = datetime.now().isoformat()
            passenger['updated_at'] = datetime.now().isoformat()
            
            # Save the updated passenger data
            response = requests.put(f"{BASE_URL}/users/{passenger['id']}", json=passenger)
            response.raise_for_status()
            
            # Update ban records to set them as inactive
            try:
                # Find active bans for this user
                ban_response = requests.get(f"{BASE_URL}/bans/query?user_id={passenger['id']}&active=true")
                if ban_response.status_code == 200:
                    bans = ban_response.json()
                    
                    # Update each ban to set active = false
                    for ban in bans:
                        ban['active'] = False
                        ban['unbanned_by'] = admin_user['id']
                        ban['unbanned_at'] = datetime.now().isoformat()
                        
                        requests.put(f"{BASE_URL}/bans/{ban['id']}", json=ban)
            except requests.RequestException:
                # If updating ban records fails, it's not critical - continue
                pass
            
            return passenger
            
        except requests.RequestException as e:
            raise UserServiceError(f"Failed to unban passenger: {str(e)}")
        except AuthError as e:
            raise  # Re-throw auth errors without wrapping

    @staticmethod
    def get_ban_status(user_id: str) -> Dict[str, Any]:
        """
        Get the ban status for a user.
        
        Args:
            user_id: ID of the user to check
            
        Returns:
            Dict: Ban status information
            
        Raises:
            UserServiceError: If checking ban status fails
        """
        try:
            # Get user data
            response = requests.get(f"{BASE_URL}/users/{user_id}")
            
            if response.status_code == 404:
                raise UserServiceError(f"User with ID {user_id} not found")
                
            response.raise_for_status()
            user = response.json()
            
            # Check if banned
            is_banned = user.get('is_banned', False)
            
            ban_info = {
                'is_banned': is_banned,
                'is_permanent': user.get('is_permanent_ban', False) if is_banned else False,
                'reason': user.get('ban_reason') if is_banned else None,
                'banned_at': user.get('banned_at') if is_banned else None
            }
            
            # Try to get additional ban details from bans collection
            if is_banned:
                try:
                    ban_response = requests.get(f"{BASE_URL}/bans/query?user_id={user_id}&active=true")
                    if ban_response.status_code == 200:
                        bans = ban_response.json()
                        if bans:
                            # Add admin information from most recent ban
                            most_recent_ban = max(bans, key=lambda b: b.get('created_at', ''))
                            ban_info['banned_by_email'] = most_recent_ban.get('admin_email')
                except requests.RequestException:
                    # If getting ban details fails, continue with basic info
                    pass
            
            return ban_info
            
        except requests.RequestException as e:
            raise UserServiceError(f"Failed to check ban status: {str(e)}")

    @staticmethod
    def list_banned_passengers(token: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        List all banned passengers.
        
        Args:
            token: JWT token for authentication (admin only)
            active_only: Whether to show only currently banned passengers
            
        Returns:
            List[Dict]: List of banned passengers
            
        Raises:
            UserServiceError: If listing banned passengers fails
            AuthError: If authentication or authorization fails
        """
        try:
            # Verify token and ensure user is an admin
            AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Get all users
            response = requests.get(f"{BASE_URL}/users")
            
            if response.status_code == 404:
                return []
                
            response.raise_for_status()
            users = response.json()
            
            # Filter to passengers only
            passengers = [u for u in users if u.get('user_type') == UserType.PASSENGER.value]
            
            # Filter to banned passengers
            if active_only:
                banned_passengers = [p for p in passengers if p.get('is_banned', False)]
            else:
                # Include passengers that have ban history (banned_at exists)
                banned_passengers = [p for p in passengers if 
                                    p.get('is_banned', False) or 
                                    p.get('banned_at') is not None]
            
            return banned_passengers
            
        except requests.RequestException as e:
            raise UserServiceError(f"Failed to list banned passengers: {str(e)}")
        except AuthError as e:
            raise  # Re-throw auth errors without wrapping