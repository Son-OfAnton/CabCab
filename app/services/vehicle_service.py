"""Vehicle service for CabCab application."""

import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4

from app.models.vehicle import Vehicle, VehicleType
from app.services.auth_service import AuthService, AuthError, UserType

# Base URL for our custom JSON server
BASE_URL = "http://localhost:3000"


class VehicleServiceError(Exception):
    """Custom exception for vehicle service errors."""
    pass


class VehicleService:
    """Service for handling vehicle operations."""
    
    @staticmethod
    def register_vehicle(token: str, make: str, model: str, year: int, color: str, 
                        license_plate: str, vehicle_type: str, capacity: int) -> Dict[str, Any]:
        """
        Register a new vehicle for a driver.
        
        Args:
            token: JWT token for authentication
            make: Vehicle manufacturer
            model: Vehicle model
            year: Vehicle year
            color: Vehicle color
            license_plate: Vehicle license plate
            vehicle_type: Type of vehicle (ECONOMY, COMFORT, PREMIUM, SUV, XL)
            capacity: Maximum passenger capacity
            
        Returns:
            Dict: Vehicle data
            
        Raises:
            VehicleServiceError: If vehicle registration fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            user = AuthService.require_user_type(token, [UserType.DRIVER.value])
            
            # Check if the license plate is already registered
            response = requests.get(f"{BASE_URL}/vehicles/query?license_plate={license_plate}")
            
            if response.status_code != 404:  # 404 means no vehicles found, which is good
                response.raise_for_status()
                existing_vehicles = response.json()
                
                if existing_vehicles:
                    raise VehicleServiceError(f"Vehicle with license plate {license_plate} is already registered")
            
            # Convert vehicle type string to enum
            try:
                veh_type = VehicleType[vehicle_type.upper()]
            except (KeyError, ValueError):
                valid_types = ", ".join([t.name for t in VehicleType])
                raise VehicleServiceError(f"Invalid vehicle type. Choose from: {valid_types}")
            
            # Create new vehicle
            vehicle_id = str(uuid4())
            new_vehicle = {
                "id": vehicle_id,
                "make": make,
                "model": model,
                "year": year,
                "color": color,
                "license_plate": license_plate,
                "vehicle_type": veh_type.name,
                "capacity": capacity,
                "driver_id": user["id"],
                "created_at": datetime.now().isoformat(),
                "is_active": True
            }
            
            # Save vehicle to database
            response = requests.post(f"{BASE_URL}/vehicles", json=new_vehicle)
            response.raise_for_status()
            saved_vehicle = response.json()
            
            # If this is the driver's first vehicle, update driver's vehicle_id
            if not user.get("vehicle_id"):
                user["vehicle_id"] = vehicle_id
                user["updated_at"] = datetime.now().isoformat()
                
                # Update user in database
                update_response = requests.put(f"{BASE_URL}/users/{user['id']}", json=user)
                update_response.raise_for_status()
            
            # FIX: Instead of returning the response JSON directly, return our created vehicle data
            # This ensures all expected fields are present even if the server response is incomplete
            # This is especially important for the first vehicle registration
            return saved_vehicle if isinstance(saved_vehicle, dict) and 'make' in saved_vehicle else new_vehicle
            
        except requests.RequestException as e:
            raise VehicleServiceError(f"Vehicle registration failed: {str(e)}")
    
    @staticmethod
    def get_vehicle_by_id(vehicle_id: str) -> Dict[str, Any]:
        """
        Get a vehicle by its ID.
        
        Args:
            vehicle_id: ID of the vehicle to retrieve
            
        Returns:
            Dict: Vehicle data
            
        Raises:
            VehicleServiceError: If vehicle retrieval fails
        """
        try:
            response = requests.get(f"{BASE_URL}/vehicles/{vehicle_id}")
            
            if response.status_code == 404:
                raise VehicleServiceError(f"Vehicle with ID {vehicle_id} not found")
                
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise VehicleServiceError(f"Failed to retrieve vehicle: {str(e)}")
    
    @staticmethod
    def get_driver_vehicles(token: str) -> List[Dict[str, Any]]:
        """
        Get all vehicles registered to a driver.
        
        Args:
            token: JWT token for authentication
            
        Returns:
            List[Dict]: List of vehicle data
            
        Raises:
            VehicleServiceError: If vehicle retrieval fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            user = AuthService.require_user_type(token, [UserType.DRIVER.value])
            
            # Get all vehicles for this driver
            response = requests.get(f"{BASE_URL}/vehicles/query?driver_id={user['id']}")
            
            if response.status_code == 404:
                # No vehicles found, return empty list
                return []
                
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise VehicleServiceError(f"Failed to retrieve vehicles: {str(e)}")
    
    @staticmethod
    def update_vehicle(token: str, vehicle_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a vehicle's information.
        
        Args:
            token: JWT token for authentication
            vehicle_id: ID of the vehicle to update
            updates: Dictionary of fields to update
            
        Returns:
            Dict: Updated vehicle data
            
        Raises:
            VehicleServiceError: If vehicle update fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            user = AuthService.require_user_type(token, [UserType.DRIVER.value])
            
            # Get the vehicle
            vehicle = VehicleService.get_vehicle_by_id(vehicle_id)
            
            # Check if vehicle belongs to this driver
            if vehicle.get("driver_id") != user["id"]:
                raise VehicleServiceError("You do not have permission to update this vehicle.")
            
            # Update fields
            for key, value in updates.items():
                if key in ["id", "driver_id", "created_at"]:
                    # Skip protected fields
                    continue
                    
                if key == "vehicle_type" and isinstance(value, str):
                    # Convert vehicle type string to enum
                    try:
                        veh_type = VehicleType[value.upper()]
                        vehicle[key] = veh_type.name
                    except (KeyError, ValueError):
                        valid_types = ", ".join([t.name for t in VehicleType])
                        raise VehicleServiceError(f"Invalid vehicle type. Choose from: {valid_types}")
                else:
                    vehicle[key] = value
            
            # Save updated vehicle
            response = requests.put(f"{BASE_URL}/vehicles/{vehicle_id}", json=vehicle)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            raise VehicleServiceError(f"Failed to update vehicle: {str(e)}")
    
    @staticmethod
    def delete_vehicle(token: str, vehicle_id: str) -> bool:
        """
        Delete a vehicle.
        
        Args:
            token: JWT token for authentication
            vehicle_id: ID of the vehicle to delete
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            VehicleServiceError: If vehicle deletion fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            user = AuthService.require_user_type(token, [UserType.DRIVER.value])
            
            # Get the vehicle
            vehicle = VehicleService.get_vehicle_by_id(vehicle_id)
            
            # Check if vehicle belongs to this driver
            if vehicle.get("driver_id") != user["id"]:
                raise VehicleServiceError("You do not have permission to delete this vehicle.")
            
            # If this is the driver's primary vehicle, update driver
            if user.get("vehicle_id") == vehicle_id:
                # Find another vehicle to set as primary, or set to None
                other_vehicles = VehicleService.get_driver_vehicles(token)
                other_vehicles = [v for v in other_vehicles if v["id"] != vehicle_id]
                
                user["vehicle_id"] = other_vehicles[0]["id"] if other_vehicles else None
                user["updated_at"] = datetime.now().isoformat()
                
                # Update user in database
                response = requests.put(f"{BASE_URL}/users/{user['id']}", json=user)
                response.raise_for_status()
            
            # Delete the vehicle
            response = requests.delete(f"{BASE_URL}/vehicles/{vehicle_id}")
            response.raise_for_status()
            
            return True
            
        except requests.RequestException as e:
            raise VehicleServiceError(f"Failed to delete vehicle: {str(e)}")
        
    # New method to add to VehicleService class

    @staticmethod
    def find_vehicle_by_license_plate(token: str, license_plate: str) -> Dict[str, Any]:
        """
        Find a vehicle by its license plate (admin function).
        
        Args:
            token: JWT token for authentication (admin only)
            license_plate: The license plate to search for
            
        Returns:
            Dict: Vehicle data with driver details if found
            
        Raises:
            VehicleServiceError: If search fails or no vehicle found
            AuthError: If authentication or authorization fails
        """
        try:
            # Verify token and ensure user is an admin
            user = AuthService.require_user_type(token, [UserType.ADMIN.value])
            
            # Sanitize the license plate for search
            # Remove spaces, convert to uppercase
            sanitized_plate = license_plate.strip().replace(" ", "").upper()
            
            if not sanitized_plate:
                raise VehicleServiceError("License plate cannot be empty")
            
            # Query the database for vehicle with matching license plate
            # Use fuzzy matching for more flexible search
            response = requests.get(f"{BASE_URL}/vehicles")
            
            if response.status_code != 200:
                raise VehicleServiceError("Failed to retrieve vehicles")
                
            vehicles = response.json()
            
            # Filter vehicles to find matching license plates
            # Normalize license plates for comparison by removing spaces and case sensitivity
            matched_vehicles = []
            for vehicle in vehicles:
                if 'license_plate' in vehicle:
                    normalized_plate = vehicle['license_plate'].replace(" ", "").upper()
                    # Check if the normalized plate contains or matches the search term
                    if sanitized_plate in normalized_plate or normalized_plate in sanitized_plate:
                        matched_vehicles.append(vehicle)
            
            if not matched_vehicles:
                raise VehicleServiceError(f"No vehicle found with license plate similar to '{license_plate}'")
                
            # Get driver details for each matched vehicle
            for vehicle in matched_vehicles:
                if vehicle.get('driver_id'):
                    try:
                        driver_response = requests.get(f"{BASE_URL}/users/{vehicle['driver_id']}")
                        if driver_response.status_code == 200:
                            driver = driver_response.json()
                            # Add basic driver info to the vehicle data
                            vehicle['driver'] = {
                                'id': driver.get('id'),
                                'name': f"{driver.get('first_name', '')} {driver.get('last_name', '')}".strip(),
                                'email': driver.get('email'),
                                'phone': driver.get('phone'),
                                'is_verified': driver.get('is_verified', False),
                                'is_active': driver.get('is_active', True)
                            }
                    except Exception:
                        # If we can't get driver details, continue without them
                        pass
            
            return {
                'vehicles': matched_vehicles,
                'count': len(matched_vehicles)
            }
            
        except requests.RequestException as e:
            raise VehicleServiceError(f"Failed to search for vehicle: {str(e)}")
        except AuthError:
            raise  # Re-throw auth errors without wrapping