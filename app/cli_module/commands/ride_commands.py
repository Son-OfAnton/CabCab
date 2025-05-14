"""Ride commands for the CabCab CLI."""

import click
import requests
from tabulate import tabulate
from datetime import datetime

from app.services.ride_service import RideService, RideServiceError
from app.services.auth_service import AuthError, UserType
from app.cli_module.utils import get_token, require_user_type


@click.group(name="ride")
def ride_group():
    """Ride management commands."""
    pass


@ride_group.command(name="request")
@click.option("--pickup", prompt="Pickup location", help="Full pickup location address")
@click.option("--dropoff", prompt="Dropoff location", help="Full dropoff location address")
@require_user_type([UserType.PASSENGER.value])
def request_ride(pickup, dropoff):
    """Request a new ride with pickup and dropoff locations."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Parse the location strings
        # This is simplified - in a real app we'd use geocoding to validate and get components
        pickup_parts = _parse_location(pickup)
        dropoff_parts = _parse_location(dropoff)
        
        ride = RideService.create_ride_request(
            token,
            pickup_parts.get('address', pickup),      # Use full string as address if parsing fails
            pickup_parts.get('city', 'Unknown City'), 
            pickup_parts.get('state', 'Unknown State'),
            pickup_parts.get('postal', '00000'),
            pickup_parts.get('country', 'USA'),
            dropoff_parts.get('address', dropoff),    # Use full string as address if parsing fails
            dropoff_parts.get('city', 'Unknown City'),
            dropoff_parts.get('state', 'Unknown State'),
            dropoff_parts.get('postal', '00000'),
            dropoff_parts.get('country', 'USA')
        )

        click.echo("\n🚗 Ride request created successfully! 🚗\n")
        click.echo(f"Ride ID: {ride['id']}")
        click.echo(f"Status: {ride['status']}")
        
        # Display pickup and dropoff details
        click.echo("\n📍 Pickup Location:")
        click.echo(f"   {pickup}")
        
        click.echo("\n🏁 Dropoff Location:")
        click.echo(f"   {dropoff}")
        
        # Display ride estimates
        click.echo("\n📊 Ride Estimates:")
        click.echo(f"   Distance: {ride['distance']} km")
        click.echo(f"   Duration: {ride['duration']} minutes")
        click.echo(f"   Estimated Fare: ${ride['estimated_fare']}")
        
        click.echo("\nWe're looking for a driver to accept your ride request...")
        click.echo("Use 'cabcab ride status' to check the status of your ride.")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


def _parse_location(location_str):
    """
    Attempt to parse location string into components.
    
    This is a simple parser that tries to extract city, state, postal code
    from a location string. In a real app, we'd use a geocoding service.
    
    Returns a dict with address components.
    """
    result = {
        'address': location_str,
        'city': 'Unknown City',
        'state': 'Unknown State',
        'postal': '00000',
        'country': 'USA'
    }
    
    # Very basic parsing - just an example
    parts = location_str.split(',')
    if len(parts) >= 3:
        # Format might be like "123 Main St, Boston, MA 02108"
        result['address'] = parts[0].strip()
        result['city'] = parts[1].strip()
        
        # Try to parse state and zip
        state_zip = parts[2].strip().split()
        if len(state_zip) >= 1:
            result['state'] = state_zip[0]
        if len(state_zip) >= 2:
            result['postal'] = state_zip[1]
            
    elif len(parts) == 2:
        # Format might be like "123 Main St, Boston"
        result['address'] = parts[0].strip()
        result['city'] = parts[1].strip()
        
    # If there's a country specified
    if len(parts) >= 4:
        result['country'] = parts[3].strip()
        
    return result


@ride_group.command(name="list")
@click.option("--status", help="Filter by ride status")
@require_user_type([UserType.PASSENGER.value])
def list_rides(status):
    """View your ride history with optional status filtering."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        rides = RideService.get_user_rides(token, status)

        if not rides:
            click.echo("You have no rides." + 
                      (f" with status '{status}'" if status else ""))
            return

        # Prepare data for table
        table_data = []
        for ride in rides:
            # Parse ISO datetime to more readable format
            request_time = None
            if ride.get('request_time'):
                try:
                    dt = datetime.fromisoformat(ride['request_time'].replace('Z', '+00:00'))
                    request_time = dt.strftime('%Y-%m-%d %H:%M')
                except (ValueError, TypeError):
                    request_time = ride['request_time']
                    
            table_data.append([
                ride.get('id'),
                ride.get('status'),
                request_time,
                f"${ride.get('estimated_fare')}",
                f"{ride.get('distance')} km",
                f"{ride.get('duration')} min"
            ])

        click.echo(tabulate(
            table_data,
            headers=["Ride ID", "Status", "Requested", "Fare", "Distance", "Duration"],
            tablefmt="pretty"
        ))
        
        click.echo("\nUse 'cabcab ride status' to view details of your most recent ride.")
        click.echo("Or 'cabcab ride status <ride_id>' to view details of a specific ride.")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ride_group.command(name="status")
@click.argument("ride_id", required=False)
def ride_status(ride_id):
    """
    Check the status and details of a ride.
    
    If no ride_id is provided, shows the status of your most recent ride.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # If no ride_id is provided, get the most recent ride
        if not ride_id:
            rides = RideService.get_user_rides(token)
            if not rides:
                click.echo("You have no ride history.")
                return
                
            # Get the most recent ride (already sorted in get_user_rides)
            most_recent_ride = rides[0]
            ride_id = most_recent_ride['id']
            click.echo(f"Showing your most recent ride (ID: {ride_id})")
        
        ride = RideService.get_ride_by_id(ride_id)
        
        # Format request time
        request_time = None
        if ride.get('request_time'):
            try:
                dt = datetime.fromisoformat(ride['request_time'].replace('Z', '+00:00'))
                request_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                request_time = ride['request_time']

        click.echo(f"\n🚖 Ride Details (ID: {ride['id']})\n")
        click.echo(f"Status: {ride['status']}")
        click.echo(f"Requested: {request_time}")
        
        # Display pickup and dropoff details
        pickup = ride.get('pickup_location', {})
        dropoff = ride.get('dropoff_location', {})
        
        # Format full addresses for display
        pickup_address = f"{pickup.get('address')}, {pickup.get('city')}, {pickup.get('state')} {pickup.get('postal_code')}"
        dropoff_address = f"{dropoff.get('address')}, {dropoff.get('city')}, {dropoff.get('state')} {dropoff.get('postal_code')}"
        
        click.echo("\n📍 Pickup Location:")
        click.echo(f"   {pickup_address}")
        
        click.echo("\n🏁 Dropoff Location:")
        click.echo(f"   {dropoff_address}")
        
        # Display ride estimates
        click.echo("\n📊 Ride Information:")
        click.echo(f"   Distance: {ride.get('distance')} km")
        click.echo(f"   Duration: {ride.get('duration')} minutes")
        click.echo(f"   Estimated Fare: ${ride.get('estimated_fare')}")
        
        # Display rating if available
        if ride.get('rating'):
            click.echo(f"   Rating: {'★' * ride.get('rating')}{' ' * (5 - ride.get('rating'))} ({ride.get('rating')}/5)")
            if ride.get('feedback'):
                click.echo(f"   Feedback: \"{ride.get('feedback')}\"")
        
        # Display driver information if assigned
        if ride.get('driver_id'):
            click.echo("\n👤 Driver Information:")
            
            # Fetch detailed driver information
            try:
                response = requests.get(f"http://localhost:3000/users/{ride.get('driver_id')}")
                if response.status_code == 200:
                    driver = response.json()
                    click.echo(f"   Name: {driver.get('first_name', '')} {driver.get('last_name', '')}")
                    click.echo(f"   Phone: {driver.get('phone', 'Not available')}")
                    click.echo(f"   Rating: {driver.get('rating', 'N/A')}")
                    
                    # Try to get vehicle information
                    vehicle_id = driver.get('vehicle_id')
                    if vehicle_id:
                        try:
                            vehicle_response = requests.get(f"http://localhost:3000/vehicles/{vehicle_id}")
                            if vehicle_response.status_code == 200:
                                vehicle = vehicle_response.json()
                                click.echo(f"   Vehicle: {vehicle.get('make', '')} {vehicle.get('model', '')} ({vehicle.get('color', '')})")
                                click.echo(f"   License Plate: {vehicle.get('license_plate', 'Not available')}")
                        except Exception:
                            click.echo(f"   Vehicle information not available")
                else:
                    # Fallback if we can't get driver details
                    click.echo(f"   Driver ID: {ride.get('driver_id')}")
                    click.echo(f"   (Detailed driver information not available)")
            except Exception:
                # Fallback if API request fails
                click.echo(f"   Driver ID: {ride.get('driver_id')}")
                click.echo(f"   (Detailed driver information not available)")
        
        # Show ride actions based on status
        click.echo("\nAvailable Actions:")
        if ride.get('status') in ["REQUESTED", "DRIVER_ASSIGNED"]:
            click.echo("   - Cancel this ride with 'cabcab ride cancel " + ride_id + "'")
        elif ride.get('status') == "COMPLETED":
            if not ride.get('rating'):
                click.echo("   - Rate this ride with 'cabcab ride rate " + ride_id + "'")
        
    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ride_group.command(name="cancel")
@click.argument("ride_id", required=False)
@click.option("--confirm", is_flag=True, help="Confirm cancellation without prompting")
def cancel_ride(ride_id, confirm):
    """
    Cancel a ride request.
    
    If no ride_id is provided, cancels your most recent active ride.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # If no ride_id is provided, get the most recent cancelable ride
        if not ride_id:
            rides = RideService.get_user_rides(token)
            
            if not rides:
                click.echo("You have no ride history.")
                return
            
            # Filter for rides that could be cancelled
            cancelable_rides = [r for r in rides if r.get('status') in ["REQUESTED", "DRIVER_ASSIGNED"]]
            
            if not cancelable_rides:
                click.echo("You have no active rides that can be cancelled.")
                return
                
            # Get the most recent cancelable ride
            ride_id = cancelable_rides[0]['id']
            click.echo(f"Cancelling your most recent active ride (ID: {ride_id})")
        
        # Get ride details
        ride = RideService.get_ride_by_id(ride_id)
        
        pickup = ride.get('pickup_location', {})
        dropoff = ride.get('dropoff_location', {})
        
        # Format addresses for display
        pickup_address = f"{pickup.get('address')}, {pickup.get('city')}"
        dropoff_address = f"{dropoff.get('address')}, {dropoff.get('city')}"
        
        click.echo(f"Cancelling ride from:")
        click.echo(f"   {pickup_address}")
        click.echo(f"To:")
        click.echo(f"   {dropoff_address}")
        
        # Confirm cancellation
        if not confirm and not click.confirm("Are you sure you want to cancel this ride?"):
            click.echo("Ride cancellation cancelled.")
            return

        # Cancel the ride
        cancelled_ride = RideService.cancel_ride(token, ride_id)
        
        click.echo("\n✅ Ride cancelled successfully!")
        click.echo(f"Ride ID: {cancelled_ride['id']}")
        click.echo(f"Status: {cancelled_ride['status']}")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ride_group.command(name="rate")
@click.argument("ride_id", required=False)
@click.option("--rating", type=click.IntRange(1, 5), prompt=True, 
              help="Rate your ride (1-5 stars)")
@click.option("--feedback", prompt="Additional feedback (optional)", 
              default="", help="Additional feedback about your ride")
@require_user_type([UserType.PASSENGER.value])
def rate_ride(ride_id, rating, feedback):
    """
    Rate a completed ride.
    
    If no ride_id is provided, rates your most recent completed ride.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # If no ride_id is provided, get the most recent completed ride
        if not ride_id:
            rides = RideService.get_user_rides(token)
            
            if not rides:
                click.echo("You have no ride history.")
                return
            
            # Filter for completed rides that haven't been rated
            completed_rides = [r for r in rides if r.get('status') == "COMPLETED" and not r.get('rating')]
            
            if not completed_rides:
                click.echo("You have no completed rides that need rating.")
                return
                
            # Get the most recent completed ride
            ride_id = completed_rides[0]['id']
            click.echo(f"Rating your most recent completed ride (ID: {ride_id})")
        
        # Rate the ride
        rated_ride = RideService.rate_ride(token, ride_id, rating, feedback)
        
        # Display success message
        click.echo("\n⭐ Ride rated successfully! ⭐")
        click.echo(f"Ride ID: {rated_ride['id']}")
        click.echo(f"Rating: {'★' * rating}{' ' * (5 - rating)} ({rating}/5)")
        if feedback:
            click.echo(f"Feedback: \"{feedback}\"")
            
        click.echo("\nThank you for your feedback! Your rating helps us improve our service.")
        click.echo("It also helps good drivers get more ride requests.")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)