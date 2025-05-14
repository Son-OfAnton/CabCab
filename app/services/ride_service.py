"""Ride service for CabCab application."""

import os
import json
import requests
import math
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID, uuid4

from app.models.ride import Ride, RideStatus
from app.models.location import Location
from app.services.auth_service import AuthService, AuthError, UserType

# Base URL for our custom JSON server
BASE_URL = "http://localhost:3000"


class RideServiceError(Exception):
    """Custom exception for ride service errors."""
    pass


class RideService:
    """Service for handling ride operations."""
    
    @staticmethod
    def create_ride_request(token: str, pickup_address: str, pickup_city: str, pickup_state: str, 
                           pickup_postal: str, pickup_country: str, 
                           dropoff_address: str, dropoff_city: str, dropoff_state: str,
                           dropoff_postal: str, dropoff_country: str) -> Dict[str, Any]:
        """
        Create a new ride request.
        
        Args:
            token: JWT token for authentication
            pickup_address: Street address for pickup
            pickup_city: City for pickup
            pickup_state: State for pickup
            pickup_postal: Postal code for pickup
            pickup_country: Country for pickup
            dropoff_address: Street address for dropoff
            dropoff_city: City for dropoff
            dropoff_state: State for dropoff
            dropoff_postal: Postal code for dropoff
            dropoff_country: Country for dropoff
            
        Returns:
            Dict: Ride data
            
        Raises:
            RideServiceError: If ride request creation fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a passenger
            user = AuthService.require_user_type(token, [UserType.PASSENGER.value])
            
            # Create pickup location - for a real app, we'd use a geocoding API to get coordinates
            # Simulating coordinates for the purpose of this implementation
            pickup_lat, pickup_lng = _generate_coordinates_for_location(pickup_address)
            pickup_location = {
                "id": str(uuid4()),
                "latitude": pickup_lat,
                "longitude": pickup_lng,
                "address": pickup_address,
                "city": pickup_city,
                "state": pickup_state,
                "postal_code": pickup_postal,
                "country": pickup_country,
                "user_id": user["id"]
            }
            
            # Create dropoff location
            dropoff_lat, dropoff_lng = _generate_coordinates_for_location(dropoff_address)
            dropoff_location = {
                "id": str(uuid4()),
                "latitude": dropoff_lat,
                "longitude": dropoff_lng,
                "address": dropoff_address,
                "city": dropoff_city,
                "state": dropoff_state,
                "postal_code": dropoff_postal,
                "country": dropoff_country,
                "user_id": user["id"]
            }
            
            # Save pickup location
            response = requests.post(f"{BASE_URL}/locations", json=pickup_location)
            response.raise_for_status()
            saved_pickup = response.json()
            
            # Save dropoff location
            response = requests.post(f"{BASE_URL}/locations", json=dropoff_location)
            response.raise_for_status()
            saved_dropoff = response.json()
            
            # Calculate ride estimation
            distance, duration, fare = _calculate_ride_estimation(
                pickup_lat, pickup_lng, dropoff_lat, dropoff_lng
            )
            
            # Create ride request
            ride_id = str(uuid4())
            new_ride = {
                "id": ride_id,
                "user_id": user["id"],
                "pickup_location_id": saved_pickup["id"],
                "dropoff_location_id": saved_dropoff["id"],
                "request_time": datetime.now().isoformat(),
                "status": RideStatus.REQUESTED.name,
                "estimated_fare": fare,
                "distance": distance,
                "duration": duration,
                "driver_id": None,
                "start_time": None,
                "end_time": None,
                "actual_fare": None,
                "payment_id": None,
                "rating": None,
                "feedback": None
            }
            
            # Save ride
            response = requests.post(f"{BASE_URL}/rides", json=new_ride)
            response.raise_for_status()
            saved_ride = response.json()
            
            # Add location details for convenience
            saved_ride["pickup_location"] = saved_pickup
            saved_ride["dropoff_location"] = saved_dropoff
            
            return saved_ride
            
        except requests.RequestException as e:
            raise RideServiceError(f"Ride request creation failed: {str(e)}")

    @staticmethod
    def accept_ride(token: str, ride_id: str) -> Dict[str, Any]:
        """
        Accept a ride request as a driver.
        
        Args:
            token: JWT token for authentication
            ride_id: ID of the ride to accept
            
        Returns:
            Dict: Updated ride data
            
        Raises:
            RideServiceError: If ride acceptance fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            driver = AuthService.require_user_type(token, [UserType.DRIVER.value])
            
            # Check if driver is verified and available
            if not driver.get("is_verified", False):
                raise RideServiceError("You must be verified to accept ride requests.")
            
            if not driver.get("is_available", False):
                raise RideServiceError("You must set your status to available before accepting rides.")
                
            # Get the ride
            ride = RideService.get_ride_by_id(ride_id, include_locations=False)
            
            # Check if ride can be accepted
            if ride.get("status") != RideStatus.REQUESTED.name:
                raise RideServiceError(f"Cannot accept ride with status {ride.get('status')}.")
            
            if ride.get("driver_id"):
                raise RideServiceError("This ride has already been accepted by another driver.")
            
            # Update ride with driver info
            ride["driver_id"] = driver["id"]
            ride["status"] = RideStatus.DRIVER_ASSIGNED.name
            
            # Save updated ride
            response = requests.put(f"{BASE_URL}/rides/{ride_id}", json=ride)
            response.raise_for_status()
            updated_ride = response.json()
            
            # Get location info for the response
            return RideService.get_ride_by_id(ride_id)
            
        except requests.RequestException as e:
            raise RideServiceError(f"Failed to accept ride: {str(e)}")
    
    @staticmethod
    def get_ride_by_id(ride_id: str, include_locations: bool = True, include_driver_details: bool = False) -> Dict[str, Any]:
        """
        Get a ride by its ID.
        
        Args:
            ride_id: ID of the ride to retrieve
            include_locations: Whether to include location details
            include_driver_details: Whether to include detailed driver info
            
        Returns:
            Dict: Ride data with location details if requested
            
        Raises:
            RideServiceError: If ride retrieval fails
        """
        try:
            response = requests.get(f"{BASE_URL}/rides/{ride_id}")
            
            if response.status_code == 404:
                raise RideServiceError(f"Ride with ID {ride_id} not found")
                
            response.raise_for_status()
            ride = response.json()
            
            # Add location details if requested
            if include_locations and "pickup_location" not in ride and "dropoff_location" not in ride:
                # Get pickup location
                pickup_loc_id = ride.get("pickup_location_id")
                if pickup_loc_id:
                    try:
                        pickup_response = requests.get(f"{BASE_URL}/locations/{pickup_loc_id}")
                        if pickup_response.status_code == 200:
                            ride["pickup_location"] = pickup_response.json()
                    except requests.RequestException:
                        pass
                
                # Get dropoff location
                dropoff_loc_id = ride.get("dropoff_location_id")
                if dropoff_loc_id:
                    try:
                        dropoff_response = requests.get(f"{BASE_URL}/locations/{dropoff_loc_id}")
                        if dropoff_response.status_code == 200:
                            ride["dropoff_location"] = dropoff_response.json()
                    except requests.RequestException:
                        pass
            
            # Add driver details if requested and available
            if include_driver_details and ride.get("driver_id"):
                driver_id = ride.get("driver_id")
                try:
                    driver_response = requests.get(f"{BASE_URL}/users/{driver_id}")
                    if driver_response.status_code == 200:
                        driver = driver_response.json()
                        ride["driver"] = driver
                        
                        # Add vehicle details if available
                        vehicle_id = driver.get("vehicle_id")
                        if vehicle_id:
                            try:
                                vehicle_response = requests.get(f"{BASE_URL}/vehicles/{vehicle_id}")
                                if vehicle_response.status_code == 200:
                                    ride["vehicle"] = vehicle_response.json()
                            except requests.RequestException:
                                pass
                except requests.RequestException:
                    pass
                    
            return ride
            
        except requests.RequestException as e:
            raise RideServiceError(f"Failed to retrieve ride: {str(e)}")
    
    @staticmethod
    def get_user_rides(token: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all rides for a user.
        
        Args:
            token: JWT token for authentication
            status: Optional filter by ride status
            
        Returns:
            List[Dict]: List of ride data
            
        Raises:
            RideServiceError: If ride retrieval fails
            AuthError: If authentication fails
        """
        try:
            # Verify token 
            user = AuthService.verify_token(token)
            
            # Get all rides for this user
            if status:
                response = requests.get(f"{BASE_URL}/rides/query?user_id={user['id']}&status={status}")
            else:
                response = requests.get(f"{BASE_URL}/rides/query?user_id={user['id']}")
            
            if response.status_code == 404:
                # No rides found, return empty list
                return []
                
            response.raise_for_status()
            
            # Sort rides by request time, most recent first
            rides = response.json()
            rides.sort(key=lambda r: r.get('request_time', ""), reverse=True)
            
            return rides
            
        except requests.RequestException as e:
            raise RideServiceError(f"Failed to retrieve rides: {str(e)}")
            
    @staticmethod
    def get_driver_rides(token: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all rides assigned to a driver.
        
        Args:
            token: JWT token for authentication
            status: Optional filter by ride status
            
        Returns:
            List[Dict]: List of ride data
            
        Raises:
            RideServiceError: If ride retrieval fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            driver = AuthService.require_user_type(token, [UserType.DRIVER.value])
            
            # Get all rides for this driver
            if status:
                response = requests.get(f"{BASE_URL}/rides/query?driver_id={driver['id']}&status={status}")
            else:
                response = requests.get(f"{BASE_URL}/rides/query?driver_id={driver['id']}")
            
            if response.status_code == 404:
                # No rides found, return empty list
                return []
                
            response.raise_for_status()
            
            # Sort rides by request time, most recent first
            rides = response.json()
            rides.sort(key=lambda r: r.get('request_time', ""), reverse=True)
            
            return rides
            
        except requests.RequestException as e:
            raise RideServiceError(f"Failed to retrieve rides: {str(e)}")
    
    @staticmethod
    def get_available_rides(token: str) -> List[Dict[str, Any]]:
        """
        Get all available ride requests that a driver can accept.
        
        Args:
            token: JWT token for authentication
            
        Returns:
            List[Dict]: List of available ride data with location details
            
        Raises:
            RideServiceError: If ride retrieval fails
            AuthError: If authentication fails
        """
        try:
            # Verify token and ensure user is a driver
            driver = AuthService.require_user_type(token, [UserType.DRIVER.value])
            
            # Check if driver is verified and available
            if not driver.get("is_verified", False):
                raise RideServiceError("You must be verified to see available rides.")
            
            if not driver.get("is_available", False):
                raise RideServiceError("You must set your status to available to see ride requests.")
            
            # Get all rides with status REQUESTED
            response = requests.get(f"{BASE_URL}/rides/query?status={RideStatus.REQUESTED.name}")
            
            if response.status_code == 404:
                # No rides found, return empty list
                return []
                
            response.raise_for_status()
            rides = response.json()
            
            # Sort rides by request time, oldest first (FIFO for fairness)
            rides.sort(key=lambda r: r.get('request_time', ""))
            
            # Add location details for each ride
            detailed_rides = []
            for ride in rides:
                try:
                    detailed_ride = RideService.get_ride_by_id(ride['id'])
                    detailed_rides.append(detailed_ride)
                except RideServiceError:
                    # Skip rides with missing location info
                    continue
            
            return detailed_rides
            
        except requests.RequestException as e:
            raise RideServiceError(f"Failed to retrieve available rides: {str(e)}")
    
    @staticmethod
    def cancel_ride(token: str, ride_id: str) -> Dict[str, Any]:
        """
        Cancel an existing ride request.
        
        Args:
            token: JWT token for authentication
            ride_id: ID of the ride to cancel
            
        Returns:
            Dict: Updated ride data
            
        Raises:
            RideServiceError: If ride cancellation fails
            AuthError: If authentication fails
        """
        try:
            # Verify token
            user = AuthService.verify_token(token)
            
            # Get the ride
            ride = RideService.get_ride_by_id(ride_id, include_locations=False)
            
            # Check if ride belongs to this user
            if ride.get("user_id") != user["id"]:
                raise RideServiceError("You do not have permission to cancel this ride.")
            
            # Check if ride can be cancelled
            if ride.get("status") not in [RideStatus.REQUESTED.name, RideStatus.DRIVER_ASSIGNED.name]:
                raise RideServiceError(f"Cannot cancel ride with status {ride.get('status')}.")
            
            # Update ride status
            ride["status"] = RideStatus.CANCELLED.name
            
            # Save updated ride
            response = requests.put(f"{BASE_URL}/rides/{ride_id}", json=ride)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            raise RideServiceError(f"Failed to cancel ride: {str(e)}")

    @staticmethod
    def rate_ride(token: str, ride_id: str, rating: int, feedback: str = "") -> Dict[str, Any]:
        """
        Rate a completed ride and provide feedback.
        
        Args:
            token: JWT token for authentication
            ride_id: ID of the ride to rate
            rating: Rating value (1-5 stars)
            feedback: Optional feedback text
            
        Returns:
            Dict: Updated ride data
            
        Raises:
            RideServiceError: If ride rating fails
            AuthError: If authentication fails
        """
        try:
            # Verify token
            user = AuthService.verify_token(token)
            
            # Validate rating
            if not 1 <= rating <= 5:
                raise RideServiceError("Rating must be between 1 and 5 stars.")
                
            # Get the ride
            ride = RideService.get_ride_by_id(ride_id, include_locations=False)
            
            # Check if ride belongs to this user
            if ride.get("user_id") != user["id"]:
                raise RideServiceError("You can only rate your own rides.")
            
            # Check if ride is completed
            if ride.get("status") != RideStatus.COMPLETED.name:
                raise RideServiceError("Only completed rides can be rated.")
                
            # Check if ride has already been rated
            if ride.get("rating") is not None:
                raise RideServiceError("This ride has already been rated.")
            
            # Update ride with rating
            ride["rating"] = rating
            ride["feedback"] = feedback
            
            # Save updated ride
            response = requests.put(f"{BASE_URL}/rides/{ride_id}", json=ride)
            response.raise_for_status()
            updated_ride = response.json()
            
            # Update driver rating if a driver was assigned
            driver_id = ride.get("driver_id")
            if driver_id:
                try:
                    # Get driver details
                    driver_response = requests.get(f"{BASE_URL}/users/{driver_id}")
                    if driver_response.status_code == 200:
                        driver = driver_response.json()
                        
                        # Calculate new rating
                        current_rating = driver.get("rating", 0)
                        rating_count = driver.get("rating_count", 0)
                        
                        # Update driver rating using weighted average
                        if rating_count > 0 and current_rating:
                            new_rating_count = rating_count + 1
                            new_rating = ((current_rating * rating_count) + rating) / new_rating_count
                            
                            # Round to 2 decimal places
                            new_rating = round(new_rating, 2)
                        else:
                            new_rating_count = 1
                            new_rating = rating
                        
                        # Update driver in database
                        driver["rating"] = new_rating
                        driver["rating_count"] = new_rating_count
                        
                        driver_update_response = requests.put(f"{BASE_URL}/users/{driver_id}", json=driver)
                        driver_update_response.raise_for_status()
                except requests.RequestException as e:
                    # Don't fail the whole operation if driver rating update fails
                    # Just log the error or handle it appropriately
                    pass
                    
            return updated_ride
            
        except requests.RequestException as e:
            raise RideServiceError(f"Failed to update ride rating: {str(e)}")


def _generate_coordinates_for_location(address):
    """
    Generate simulated coordinates for a location.
    
    Args:
        address: The location address
        
    Returns:
        Tuple: (latitude, longitude)
    """
    # In a real app, we would use a geocoding service to get real coordinates
    # This is a simple hash-based approach to generate consistent coordinates
    # based on the address string
    
    # Simple hash function to generate a number from the address
    address_hash = sum(ord(c) for c in address)
    
    # Base coordinates (New York City area)
    base_lat, base_lng = 40.7128, -74.0060
    
    # Generate a small offset based on the address hash
    lat_offset = (address_hash % 100) / 100.0
    lng_offset = ((address_hash // 100) % 100) / 100.0
    
    return round(base_lat + lat_offset - 0.5, 4), round(base_lng + lng_offset - 0.5, 4)


def _calculate_ride_estimation(pickup_lat: float, pickup_lng: float, 
                             dropoff_lat: float, dropoff_lng: float) -> Tuple[float, int, float]:
    """
    Calculate distance, duration and fare estimates for a ride.
    
    Returns:
        Tuple[float, int, float]: distance (km), duration (minutes), fare ($)
    """
    # Calculate distance using Haversine formula
    R = 6371  # Earth radius in km
    lat1, lng1 = math.radians(pickup_lat), math.radians(pickup_lng)
    lat2, lng2 = math.radians(dropoff_lat), math.radians(dropoff_lng)
    
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    # Assume average speed of 30 km/h in a city
    duration = int(distance * 60 / 30)  # convert to minutes
    
    # Simple fare calculation: base fare + distance fare + time fare
    base_fare = 2.50  # Base fare in $
    distance_fare = distance * 1.25  # $1.25 per km
    time_fare = duration * 0.35  # $0.35 per minute
    
    fare = round(base_fare + distance_fare + time_fare, 2)
    
    return round(distance, 2), max(1, duration), max(5.0, fare)