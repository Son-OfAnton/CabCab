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
            
            # Create pickup location
            # In a real app, we'd use a geocoding service to get lat/lng
            # For simplicity, we'll use random coordinates
            pickup_lat, pickup_lng = 40.7128, -74.006  # NYC coordinates
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
            # Again, we'd use geocoding in a real app
            dropoff_lat, dropoff_lng = 40.7128, -73.95  # Somewhere in Brooklyn
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
            distance, duration, fare = RideService._calculate_ride_estimation(
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
    def get_ride_by_id(ride_id: str, include_locations: bool = True) -> Dict[str, Any]:
        """
        Get a ride by its ID.
        
        Args:
            ride_id: ID of the ride to retrieve
            include_locations: Whether to include location details
            
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
            
            # Include location details if requested
            if include_locations:
                # Get pickup location
                try:
                    pickup_response = requests.get(f"{BASE_URL}/locations/{ride['pickup_location_id']}")
                    pickup_response.raise_for_status()
                    ride["pickup_location"] = pickup_response.json()
                except requests.RequestException:
                    ride["pickup_location"] = {"id": ride["pickup_location_id"]}
                
                # Get dropoff location
                try:
                    dropoff_response = requests.get(f"{BASE_URL}/locations/{ride['dropoff_location_id']}")
                    dropoff_response.raise_for_status()
                    ride["dropoff_location"] = dropoff_response.json()
                except requests.RequestException:
                    ride["dropoff_location"] = {"id": ride["dropoff_location_id"]}
                    
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