"""Driver-specific commands for the CabCab CLI."""

import click
import requests
from tabulate import tabulate
from datetime import datetime

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


@driver_group.command(name="rides", help="List your assigned rides.")
@click.option("--status", help="Filter rides by status (e.g., DRIVER_ASSIGNED, IN_PROGRESS, COMPLETED)")
@require_user_type([UserType.DRIVER.value])
def list_rides(status):
    """List rides assigned to you."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        rides = RideService.get_driver_rides(token, status)

        if not rides:
            filter_text = f" with status '{status}'" if status else ""
            click.echo(f"You have no rides{filter_text}.")
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
        
        click.echo("\nUse 'cabcab driver ride-status <ride_id>' to view details of a specific ride.")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@driver_group.command(name="ride-status", help="Check the status and details of a ride assigned to you.")
@click.argument("ride_id", required=True)
@require_user_type([UserType.DRIVER.value])
def ride_status(ride_id):
    """Check details of a ride assigned to you."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        ride = RideService.get_ride_by_id(ride_id)
        
        # Verify this ride is assigned to the driver
        driver = AuthService.verify_token(token)
        if ride.get('driver_id') != driver['id']:
            click.echo(f"This ride is not assigned to you.", err=True)
            return
        
        # Format request time
        request_time = None
        if ride.get('request_time'):
            try:
                dt = datetime.fromisoformat(ride['request_time'].replace('Z', '+00:00'))
                request_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                request_time = ride['request_time']
                
        # Get passenger info if available
        passenger_name = "Unknown"
        try:
            passenger_response = requests.get(f"http://localhost:3000/users/{ride['user_id']}")
            if passenger_response.status_code == 200:
                passenger = passenger_response.json()
                passenger_name = f"{passenger.get('first_name', '')} {passenger.get('last_name', '')}".strip()
        except:
            pass

        click.echo(f"\n🚖 Ride Details (ID: {ride['id']})\n")
        click.echo(f"Status: {ride['status']}")
        click.echo(f"Requested: {request_time}")
        click.echo(f"Passenger: {passenger_name}")
        
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

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@driver_group.command(name="available-rides", help="List available ride requests that you can accept.")
@require_user_type([UserType.DRIVER.value])
def available_rides():
    """List available ride requests that you can accept."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        rides = RideService.get_available_rides(token)
        
        if not rides:
            click.echo("There are no ride requests available right now.")
            click.echo("Check back later or make sure your status is set to 'available'.")
            return
            
        click.echo(f"Found {len(rides)} available ride requests:\n")
        
        # Prepare data for table
        table_data = []
        for i, ride in enumerate(rides, 1):
            # Get pickup and dropoff details for the location column
            pickup_city = ride.get('pickup_location', {}).get('city', 'Unknown')
            dropoff_city = ride.get('dropoff_location', {}).get('city', 'Unknown')
            locations = f"{pickup_city} → {dropoff_city}"
            
            # Parse ISO datetime to more readable format
            request_time = None
            if ride.get('request_time'):
                try:
                    dt = datetime.fromisoformat(ride['request_time'].replace('Z', '+00:00'))
                    request_time = dt.strftime('%Y-%m-%d %H:%M')
                except (ValueError, TypeError):
                    request_time = ride['request_time']
            
            table_data.append([
                i,
                ride.get('id'),
                locations,
                request_time,
                f"${ride.get('estimated_fare')}",
                f"{ride.get('distance')} km",
                f"{ride.get('duration')} min"
            ])
            
        click.echo(tabulate(
            table_data,
            headers=["#", "Ride ID", "Route", "Requested", "Fare", "Distance", "Duration"],
            tablefmt="pretty"
        ))
        
        click.echo("\nUse 'cabcab driver accept-ride <ride_id>' to accept a ride.")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@driver_group.command(name="accept-ride", help="Accept a ride request.")
@click.argument("ride_id", required=True)
@require_user_type([UserType.DRIVER.value])
def accept_ride(ride_id):
    """Accept a ride request."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        ride = RideService.accept_ride(token, ride_id)
        
        # Get passenger info if available
        passenger_name = "Unknown"
        try:
            import requests
            passenger_response = requests.get(f"http://localhost:3000/users/{ride['user_id']}")
            if passenger_response.status_code == 200:
                passenger = passenger_response.json()
                passenger_name = f"{passenger.get('first_name', '')} {passenger.get('last_name', '')}".strip()
        except:
            pass
        
        click.echo("\n✅ Ride accepted successfully!\n")
        click.echo(f"Ride ID: {ride['id']}")
        click.echo(f"Status: {ride['status']}")
        click.echo(f"Passenger: {passenger_name}")
        
        # Display pickup and dropoff details
        pickup = ride.get('pickup_location', {})
        dropoff = ride.get('dropoff_location', {})
        
        # Format addresses for display
        pickup_address = f"{pickup.get('address')}, {pickup.get('city')}, {pickup.get('state')} {pickup.get('postal_code')}"
        
        click.echo("\n📍 Pickup Location:")
        click.echo(f"   {pickup_address}")
        
        click.echo(f"\nEstimated fare: ${ride.get('estimated_fare')}")
        
        click.echo("\nHead to the pickup location to meet your passenger.")
        click.echo("Use 'cabcab driver ride-status " + ride_id + "' to view ride details.")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)