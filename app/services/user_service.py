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
            users = response.json()
            
            if not users:
                raise UserServiceError(f"User with email {user_email} not found")
                
            passenger = users[0]
            
            # Verify the user is a passenger
            if passenger.get('user_type') != UserType.PASSENGER.value:
                raise UserServiceError(f"User with email {user_email} is not a passenger")
                
            # Update ban status
            passenger['is_banned'] = True
            passenger['banned_reason'] = reason
            passenger['banned_at'] = datetime.now().isoformat()
            passenger['banned_by'] = admin_user['id']
            passenger['permanent_ban'] = permanent
            passenger['updated_at'] = datetime.now().isoformat()
            
            # Save the updated passenger
            response = requests.put(f"{BASE_URL}/users/{passenger['id']}", json=passenger)
            response.raise_for_status()
            
            return response.json()
            
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
            users = response.json()
            
            if not users:
                raise UserServiceError(f"User with email {user_email} not found")
                
            passenger = users[0]
            
            # Verify the user is a passenger
            if passenger.get('user_type') != UserType.PASSENGER.value:
                raise UserServiceError(f"User with email {user_email} is not a passenger")
                
            # Check if passenger is banned
            if not passenger.get('is_banned'):
                raise UserServiceError(f"Passenger with email {user_email} is not currently banned")
                
            # Update ban status
            passenger['is_banned'] = False
            passenger['unbanned_at'] = datetime.now().isoformat()
            passenger['unbanned_by'] = admin_user['id']
            passenger['updated_at'] = datetime.now().isoformat()
            
            # Save the updated passenger
            response = requests.put(f"{BASE_URL}/users/{passenger['id']}", json=passenger)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            raise UserServiceError(f"Failed to unban passenger: {str(e)}")
        except AuthError as e:
            raise  # Re-throw auth errors without wrapping
    
    @staticmethod
    def get_ban_status(token: str, user_email: str) -> Dict[str, Any]:
        """
        Get the ban status of a passenger.
        
        Args:
            token: JWT token for authentication (admin only)
            user_email: Email of the passenger to check
            
        Returns:
            Dict: Ban status information
            
        Raises:
            UserServiceError: If getting ban status fails
            AuthError: If authentication or authorization fails
        """
        try:
            # Verify token and ensure user is an admin
            AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Find passenger by email
            response = requests.get(f"{BASE_URL}/users/query?email={user_email}")
            
            if response.status_code == 404 or not response.json():
                raise UserServiceError(f"User with email {user_email} not found")
                
            response.raise_for_status()
            users = response.json()
            
            if not users:
                raise UserServiceError(f"User with email {user_email} not found")
                
            passenger = users[0]
            
            # Verify the user is a passenger
            if passenger.get('user_type') != UserType.PASSENGER.value:
                raise UserServiceError(f"User with email {user_email} is not a passenger")
                
            # Check current ban status
            is_banned = passenger.get('is_banned', False)
            
            # Extract ban information if available
            ban_info = {
                'is_banned': is_banned,
                'user_id': passenger['id'],
                'email': passenger['email'],
                'name': f"{passenger.get('first_name', '')} {passenger.get('last_name', '')}".strip()
            }
            
            if is_banned:
                ban_info.update({
                    'banned_at': passenger.get('banned_at'),
                    'banned_reason': passenger.get('banned_reason'),
                    'permanent_ban': passenger.get('permanent_ban', False)
                })
            elif passenger.get('banned_at') is not None:
                # Include historical ban info for previously banned passengers
                ban_info.update({
                    'previously_banned': True,
                    'banned_at': passenger.get('banned_at'),
                    'unbanned_at': passenger.get('unbanned_at'),
                    'banned_reason': passenger.get('banned_reason'),
                })
                
            return ban_info
            
        except requests.RequestException as e:
            raise UserServiceError(f"Failed to get ban status: {str(e)}")
        except AuthError as e:
            raise  # Re-throw auth errors without wrapping
    
    @staticmethod
    def list_banned_passengers(token: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        List all passengers with active bans or ban history.
        
        Args:
            token: JWT token for authentication (admin only)
            active_only: If True, only currently banned passengers are returned;
                         if False, also includes passengers with ban history
            
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

    @staticmethod
    def get_driver_info(token: str, driver_id: str = None, email: str = None) -> Dict[str, Any]:
        """
        Get detailed information about a driver by ID or email.
        
        Args:
            token: JWT token for authentication (admin only)
            driver_id: Optional driver ID
            email: Optional driver email
            
        Returns:
            Dict: Combined driver information including contact details and vehicle
            
        Raises:
            UserServiceError: If finding the driver fails
            AuthError: If authentication or authorization fails
        """
        if not driver_id and not email:
            raise ValueError("Either driver_id or email must be provided")
        
        try:
            # Verify token and ensure user is an admin
            AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Find the driver user record
            if email:
                response = requests.get(f"{BASE_URL}/users/query?email={email}")
                
                if response.status_code == 404 or not response.json():
                    raise UserServiceError(f"No user found with email {email}")
                    
                response.raise_for_status()
                users = response.json()
                user = users[0]  # Get first user with this email
                
            else:  # driver_id provided
                response = requests.get(f"{BASE_URL}/users/{driver_id}")
                
                if response.status_code == 404:
                    raise UserServiceError(f"No user found with ID {driver_id}")
                    
                response.raise_for_status()
                user = response.json()
            
            # Verify the user is a driver
            if user.get('user_type') != UserType.DRIVER.value:
                raise UserServiceError("Specified user is not a driver")
            
            # Instead of requiring a separate driver record, use the user record as the base
            # for driver information since driver-specific fields may be included directly 
            # in the user record during registration
            driver = {
                "id": user.get("id"),
                "user_id": user.get("id"),  # Add user_id for backwards compatibility
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "license_number": user.get("license_number", "Not provided"),
                "rating": user.get("rating", "Not rated yet"),
                "is_active": user.get("is_active", True),
                "is_verified": user.get("is_verified", False),
                "created_at": user.get("created_at")
            }
            
            # Now try to get additional driver details if they exist in the drivers collection
            try:
                response = requests.get(f"{BASE_URL}/drivers/query?user_id={user['id']}")
                if response.status_code == 200 and response.json():
                    # We found additional driver details, merge them with our driver object
                    driver_details = response.json()[0]
                    # Update our driver object with any additional fields from driver_details
                    driver.update(driver_details)
            except Exception:
                # Don't fail if we can't get additional driver details
                pass
            
            # Try to get the driver's vehicle if they have one
            vehicle = None
            vehicle_id = driver.get('vehicle_id')
            
            if vehicle_id:
                try:
                    response = requests.get(f"{BASE_URL}/vehicles/{vehicle_id}")
                    if response.status_code == 200:
                        vehicle = response.json()
                except Exception:
                    # Don't fail if vehicle info can't be retrieved
                    pass
            else:
                # If no specific vehicle ID, check if driver has any registered vehicles
                try:
                    response = requests.get(f"{BASE_URL}/vehicles/query?driver_id={user['id']}")
                    if response.status_code == 200 and response.json():
                        vehicle = response.json()[0]  # Get the first vehicle
                except Exception:
                    # Don't fail if vehicle info can't be retrieved
                    pass
            
            # Combine all information
            result = {
                "user": user,
                "driver": driver,
                "vehicle": vehicle
            }
            
            return result
            
        except requests.RequestException as e:
            raise UserServiceError(f"Failed to retrieve driver information: {str(e)}")
        except AuthError:
            raise  # Re-throw auth errors without wrapping

    @staticmethod
    def list_all_drivers(token: str, active_only: bool = False, verified_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all drivers registered on the platform with optional filtering.
        
        Args:
            token: JWT token for authentication (admin only)
            active_only: If True, only currently active drivers are returned
            verified_only: If True, only verified drivers are returned
            
        Returns:
            List[Dict]: List of driver information objects
            
        Raises:
            UserServiceError: If listing drivers fails
            AuthError: If authentication or authorization fails
        """
        try:
            # Verify token and ensure user is an admin
            AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Get all users that are drivers
            response = requests.get(f"{BASE_URL}/users")
            if response.status_code == 404:
                return []
                
            response.raise_for_status()
            users = response.json()
            
            # Filter to drivers only
            drivers = [u for u in users if u.get('user_type') == UserType.DRIVER.value]
            
            # Apply additional filters if requested
            if active_only:
                drivers = [d for d in drivers if d.get('is_active', True)]
                
            if verified_only:
                drivers = [d for d in drivers if d.get('is_verified', False)]
                
            # Get additional driver information where available
            driver_details = []
            
            for user in drivers:
                # Basic driver info from user record
                driver_info = {
                    "id": user.get("id"),
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "email": user.get("email", ""),
                    "phone": user.get("phone", ""),
                    "license_number": user.get("license_number", ""),
                    "rating": user.get("rating", None),
                    "is_active": user.get("is_active", True),
                    "is_verified": user.get("is_verified", False),
                    "created_at": user.get("created_at", ""),
                    "user_id": user.get("id")  # Include user_id for backwards compatibility
                }
                
                # Try to get vehicle information
                try:
                    vehicle_response = requests.get(f"{BASE_URL}/vehicles/query?driver_id={user['id']}")
                    if vehicle_response.status_code == 200 and vehicle_response.json():
                        vehicle = vehicle_response.json()[0]  # Get first vehicle associated with this driver
                        driver_info["has_vehicle"] = True
                        driver_info["vehicle_id"] = vehicle.get("id")
                        driver_info["vehicle"] = f"{vehicle.get('year', '')} {vehicle.get('make', '')} {vehicle.get('model', '')}"
                        driver_info["vehicle_type"] = vehicle.get("vehicle_type", "")
                    else:
                        driver_info["has_vehicle"] = False
                except Exception:
                    driver_info["has_vehicle"] = False
                
                # Try to get driver availability status
                try:
                    driver_response = requests.get(f"{BASE_URL}/drivers/query?user_id={user['id']}")
                    if driver_response.status_code == 200 and driver_response.json():
                        driver_record = driver_response.json()[0]
                        driver_info["is_available"] = driver_record.get("is_available", False)
                        
                        # Merge any missing fields from the driver record
                        for key, value in driver_record.items():
                            if key not in driver_info or not driver_info[key]:
                                driver_info[key] = value
                    else:
                        driver_info["is_available"] = False
                except Exception:
                    driver_info["is_available"] = False
                    
                # Try to get ride statistics
                try:
                    rides_response = requests.get(f"{BASE_URL}/rides/query?driver_id={user['id']}")
                    if rides_response.status_code == 200:
                        rides = rides_response.json()
                        driver_info["total_rides"] = len(rides)
                        
                        # Count completed rides
                        completed_rides = [r for r in rides if r.get("status", "") == "COMPLETED"]
                        driver_info["completed_rides"] = len(completed_rides)
                    else:
                        driver_info["total_rides"] = 0
                        driver_info["completed_rides"] = 0
                except Exception:
                    driver_info["total_rides"] = 0
                    driver_info["completed_rides"] = 0
                
                driver_details.append(driver_info)
                
            return driver_details
            
        except requests.RequestException as e:
            raise UserServiceError(f"Failed to list drivers: {str(e)}")
        except AuthError:
            raise  # Re-throw auth errors without wrapping

    @staticmethod
    def list_all_passengers(token: str, active_only: bool = False, include_banned: bool = False) -> List[Dict[str, Any]]:
        """
        List all passengers registered on the platform with optional filtering.
        
        Args:
            token: JWT token for authentication (admin only)
            active_only: If True, only currently active passengers are returned
            include_banned: If False, banned passengers are excluded
            
        Returns:
            List[Dict]: List of passenger information objects
            
        Raises:
            UserServiceError: If listing passengers fails
            AuthError: If authentication or authorization fails
        """
        try:
            # Verify token and ensure user is an admin
            AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Get all users that are passengers
            response = requests.get(f"{BASE_URL}/users")
            
            if response.status_code == 404:
                return []
                
            response.raise_for_status()
            users = response.json()
            
            # Filter to passengers only
            passengers = [u for u in users if u.get('user_type') == UserType.PASSENGER.value]
            
            # Apply additional filters if requested
            if active_only:
                passengers = [p for p in passengers if p.get('is_active', True)]
                
            if not include_banned:
                passengers = [p for p in passengers if not p.get('is_banned', False)]
                
            # Get additional information for each passenger
            passenger_details = []
            
            for user in passengers:
                # Basic passenger info from user record
                passenger_info = {
                    "id": user.get("id"),
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "email": user.get("email", ""),
                    "phone": user.get("phone", ""),
                    "is_active": user.get("is_active", True),
                    "is_banned": user.get("is_banned", False),
                    "created_at": user.get("created_at", ""),
                }
                
                # Add ban information if available
                if passenger_info["is_banned"]:
                    passenger_info["banned_at"] = user.get("banned_at", "")
                    passenger_info["banned_reason"] = user.get("banned_reason", "No reason provided")
                    passenger_info["permanent_ban"] = user.get("permanent_ban", False)
                    
                    # If there's a banned_by ID, try to resolve it to an admin name
                    if user.get("banned_by"):
                        try:
                            admin_response = requests.get(f"{BASE_URL}/users/{user.get('banned_by')}")
                            if admin_response.status_code == 200:
                                admin = admin_response.json()
                                passenger_info["banned_by"] = f"{admin.get('first_name', '')} {admin.get('last_name', '')}".strip()
                            else:
                                passenger_info["banned_by"] = user.get("banned_by")
                        except Exception:
                            passenger_info["banned_by"] = user.get("banned_by")
                
                # Try to get payment methods count
                try:
                    payments_response = requests.get(f"{BASE_URL}/payments/query?user_id={user['id']}")
                    if payments_response.status_code == 200:
                        payments = payments_response.json()
                        # Get unique payment methods
                        payment_methods = {p.get("payment_method") for p in payments if p.get("payment_method")}
                        passenger_info["payment_methods_count"] = len(payment_methods)
                    else:
                        passenger_info["payment_methods_count"] = 0
                except Exception:
                    passenger_info["payment_methods_count"] = 0
                    
                # Try to get ride statistics
                try:
                    rides_response = requests.get(f"{BASE_URL}/rides/query?user_id={user['id']}")
                    if rides_response.status_code == 200:
                        rides = rides_response.json()
                        passenger_info["total_rides"] = len(rides)
                        
                        # Count completed rides
                        completed_rides = [r for r in rides if r.get("status", "") == "COMPLETED"]
                        passenger_info["completed_rides"] = len(completed_rides)
                        
                        # Count cancelled rides
                        cancelled_rides = [r for r in rides if r.get("status", "") == "CANCELLED"]
                        passenger_info["cancelled_rides"] = len(cancelled_rides)
                        
                        # Calculate average rating given to drivers
                        ratings = [float(r.get("driver_rating", 0)) for r in rides 
                                 if r.get("driver_rating") is not None and r.get("driver_rating") > 0]
                        
                        if ratings:
                            passenger_info["avg_rating_given"] = sum(ratings) / len(ratings)
                        else:
                            passenger_info["avg_rating_given"] = None
                    else:
                        passenger_info["total_rides"] = 0
                        passenger_info["completed_rides"] = 0
                        passenger_info["cancelled_rides"] = 0
                        passenger_info["avg_rating_given"] = None
                except Exception:
                    passenger_info["total_rides"] = 0
                    passenger_info["completed_rides"] = 0
                    passenger_info["cancelled_rides"] = 0
                    passenger_info["avg_rating_given"] = None
                
                passenger_details.append(passenger_info)
                
            return passenger_details
            
        except requests.RequestException as e:
            raise UserServiceError(f"Failed to list passengers: {str(e)}")
        except AuthError:
            raise  # Re-throw auth errors without wrapping