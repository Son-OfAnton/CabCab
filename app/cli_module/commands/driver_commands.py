"""Driver-specific commands for the CabCab CLI."""

import click
import requests
from datetime import datetime
from tabulate import tabulate

from app.services.auth_service import AuthService, AuthError, UserType
from app.services.ride_service import RideService, RideServiceError
from app.cli_module.utils import get_token, require_user_type


@click.group(name="driver")
def driver_group():
    """Driver specific commands."""
    pass


@driver_group.command(name="availability", help="Set your availability status to accept or decline ride requests.")
@click.option("--status", type=click.Choice(['available', 'unavailable']), required=True,
              help="Set your availability status")
@require_user_type([UserType.DRIVER.value])
def availability(status):
    """Set your availability to accept ride requests."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        is_available = (status == 'available')
        AuthService.set_driver_availability(token, is_available)
        click.echo(
            f"You are now {'available' if is_available else 'unavailable'} for ride requests.")
    except AuthError as e:
        click.echo(f"Error setting availability: {str(e)}", err=True)


@driver_group.command(name="rides", help="View available ride requests.")
@require_user_type([UserType.DRIVER.value])
def available_rides():
    """View available ride requests that you can accept."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get all available ride requests
        rides = RideService.get_available_rides(token)

        if not rides:
            click.echo("There are no available ride requests at this time.")
            click.echo("Check back later or ensure you are set as available.")
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

            # Format pickup and dropoff locations for display
            pickup = ride.get('pickup_location', {})
            dropoff = ride.get('dropoff_location', {})
            
            # Extract city or address information for display
            pickup_display = pickup.get('city', 'Unknown')
            if not pickup_display or pickup_display == 'Unknown City':
                # If city is not available, use the address or part of it
                address = pickup.get('address', '')
                if address:
                    # Use just the first part of the address to keep it short
                    pickup_display = address.split(',')[0] if ',' in address else address
            
            dropoff_display = dropoff.get('city', 'Unknown')
            if not dropoff_display or dropoff_display == 'Unknown City':
                address = dropoff.get('address', '')
                if address:
                    dropoff_display = address.split(',')[0] if ',' in address else address
            
            # Format the route (pickup -> dropoff)
            route = f"{pickup_display} → {dropoff_display}"
            
            # Get passenger details
            passenger = ride.get('passenger', {})
            passenger_name = f"{passenger.get('first_name', '')} {passenger.get('last_name', '')}"
            passenger_rating = passenger.get('rating', 'N/A')
                   
            table_data.append([
                ride.get('id'),
                request_time,
                route,
                passenger_name,
                passenger_rating if passenger_rating else 'N/A',
                f"${ride.get('estimated_fare')}",
                f"{ride.get('distance')} km",
                f"{ride.get('duration')} min"
            ])

        # Print available rides
        click.echo("\n🚖 Available Ride Requests:\n")
        click.echo(tabulate(
            table_data,
            headers=["Ride ID", "Requested", "Route", "Passenger", "Rating", "Est. Fare", "Distance", "Duration"],
            tablefmt="grid"
        ))
        
        click.echo("\nTo view details of a specific ride: cabcab driver ride-details <ride_id>")
        click.echo("To accept a ride: cabcab driver accept <ride_id>")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@driver_group.command(name="ride-details", help="View detailed information about a specific ride request.")
@click.argument('ride_id', required=True)
@require_user_type([UserType.DRIVER.value])
def ride_details(ride_id):
    """View detailed information about a specific ride request."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get ride details
        ride = RideService.get_ride_by_id(ride_id)
        
        # Format request time
        request_time = None
        if ride.get('request_time'):
            try:
                dt = datetime.fromisoformat(ride['request_time'].replace('Z', '+00:00'))
                request_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                request_time = ride['request_time']
                
        # Display ride details
        click.echo(f"\n🚖 Ride Details (ID: {ride['id']})\n")
        click.echo(f"Status: {ride['status']}")
        click.echo(f"Requested: {request_time}")
        
        # Display pickup and dropoff details
        pickup = ride.get('pickup_location', {})
        dropoff = ride.get('dropoff_location', {})
        
        # Format full addresses for display
        pickup_address = f"{pickup.get('address', '')}, {pickup.get('city', '')}, {pickup.get('state', '')} {pickup.get('postal_code', '')}"
        dropoff_address = f"{dropoff.get('address', '')}, {dropoff.get('city', '')}, {dropoff.get('state', '')} {dropoff.get('postal_code', '')}"
        
        click.echo("\n📍 Pickup Location:")
        click.echo(f"   {pickup_address}")
        
        click.echo("\n🏁 Dropoff Location:")
        click.echo(f"   {dropoff_address}")
        
        # Get passenger details (from ride['passenger'] or separate API call)
        try:
            passenger = ride.get('passenger', {})
            if not passenger and ride.get('user_id'):
                response = requests.get(f"http://localhost:3000/users/{ride['user_id']}")
                if response.status_code == 200:
                    passenger = response.json()
            
            if passenger:
                click.echo("\n👤 Passenger Information:")
                click.echo(f"   Name: {passenger.get('first_name', '')} {passenger.get('last_name', '')}")
                if passenger.get('rating'):
                    click.echo(f"   Rating: {passenger.get('rating')}")
        except Exception:
            # Skip passenger details if not available
            pass
        
        # Display ride estimates
        click.echo("\n📊 Ride Information:")
        click.echo(f"   Distance: {ride.get('distance')} km")
        click.echo(f"   Duration: {ride.get('duration')} minutes")
        click.echo(f"   Estimated Fare: ${ride.get('estimated_fare')}")
        
        # Show available actions
        if ride.get('status') == "REQUESTED":
            click.echo("\n✅ You can accept this ride with: cabcab driver accept " + ride_id)
        
    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@driver_group.command(name="accept", help="Accept a ride request.")
@click.argument('ride_id', required=True)
@require_user_type([UserType.DRIVER.value])
def accept_ride(ride_id):
    """Accept a ride request with the given ID."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Accept the ride
        ride = RideService.accept_ride(token, ride_id)

        # Get passenger details
        try:
            response = requests.get(f"http://localhost:3000/users/{ride['user_id']}")
            response.raise_for_status()
            passenger = response.json()
            passenger_name = f"{passenger.get('first_name', '')} {passenger.get('last_name', '')}"
        except Exception:
            passenger_name = "Unknown Passenger"

        # Format pickup and dropoff locations for display
        pickup = ride.get('pickup_location', {})
        dropoff = ride.get('dropoff_location', {})
        
        pickup_address = f"{pickup.get('address')}, {pickup.get('city')}, {pickup.get('state')}"
        dropoff_address = f"{dropoff.get('address')}, {dropoff.get('city')}, {dropoff.get('state')}"

        click.echo("\n✅ Ride accepted successfully!\n")
        click.echo(f"Ride ID: {ride['id']}")
        click.echo(f"Status: {ride['status']}")
        
        # Display passenger info
        click.echo(f"\n👤 Passenger: {passenger_name}")
        
        # Display pickup and dropoff details
        click.echo("\n📍 Pickup Location:")
        click.echo(f"   {pickup_address}")
        
        click.echo("\n🏁 Dropoff Location:")
        click.echo(f"   {dropoff_address}")
        
        # Display ride estimates
        click.echo("\n📊 Ride Information:")
        click.echo(f"   Distance: {ride['distance']} km")
        click.echo(f"   Duration: {ride['duration']} minutes")
        click.echo(f"   Estimated Fare: ${ride['estimated_fare']}")
        
        click.echo("\nYou are now unavailable for other ride requests.")
        click.echo("Use 'cabcab driver cancel <ride_id>' if you need to cancel this ride.")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error accepting ride: {str(e)}", err=True)


@driver_group.command(name="cancel", help="Cancel an accepted ride.")
@click.argument('ride_id', required=True)
@click.option("--confirm", is_flag=True, help="Confirm cancellation without prompting")
@require_user_type([UserType.DRIVER.value])
def cancel_ride(ride_id, confirm):
    """Cancel a ride you have accepted."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get ride details first
        ride = RideService.get_ride_by_id(ride_id)
        
        # Check if this driver is assigned to the ride
        user = AuthService.verify_token(token)
        if ride.get('driver_id') != user['id']:
            click.echo("You are not the assigned driver for this ride.", err=True)
            return
            
        # Format addresses for display
        pickup = ride.get('pickup_location', {})
        dropoff = ride.get('dropoff_location', {})
        
        pickup_address = f"{pickup.get('address')}, {pickup.get('city')}"
        dropoff_address = f"{dropoff.get('address')}, {dropoff.get('city')}"
        
        click.echo(f"Cancelling ride from:")
        click.echo(f"   {pickup_address}")
        click.echo(f"To:")
        click.echo(f"   {dropoff_address}")
        
        # Confirm cancellation
        if not confirm and not click.confirm("Are you sure you want to cancel this ride? This may affect your rating."):
            click.echo("Ride cancellation cancelled.")
            return

        # Cancel the ride
        cancelled_ride = RideService.cancel_ride(token, ride_id)
        
        click.echo("\n✅ Ride cancelled.")
        click.echo("You are now available for new ride requests.")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)