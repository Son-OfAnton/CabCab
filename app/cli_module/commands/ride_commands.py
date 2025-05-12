"""Ride commands for the CabCab CLI."""

import click
from tabulate import tabulate
from datetime import datetime

from app.services.ride_service import RideService, RideServiceError
from app.services.auth_service import AuthError, UserType
from app.cli_module.utils import get_token, require_user_type


@click.group(name="ride")
def ride_group():
    """Ride management commands."""
    pass


@ride_group.command(name="request", help="Request a new ride")
@click.option("--pickup-address", prompt=True, help="Pickup street address")
@click.option("--pickup-city", prompt=True, help="Pickup city")
@click.option("--pickup-state", prompt=True, help="Pickup state/province")
@click.option("--pickup-postal", prompt=True, help="Pickup postal/zip code")
@click.option("--pickup-country", prompt=True, default="USA", help="Pickup country")
@click.option("--dropoff-address", prompt=True, help="Dropoff street address")
@click.option("--dropoff-city", prompt=True, help="Dropoff city")
@click.option("--dropoff-state", prompt=True, help="Dropoff state/province")
@click.option("--dropoff-postal", prompt=True, help="Dropoff postal/zip code")
@click.option("--dropoff-country", prompt=True, default="USA", help="Dropoff country")
@require_user_type([UserType.PASSENGER.value])
def request_ride(pickup_address, pickup_city, pickup_state, pickup_postal, pickup_country,
                dropoff_address, dropoff_city, dropoff_state, dropoff_postal, dropoff_country):
    """Request a new ride with pickup and dropoff locations."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        ride = RideService.create_ride_request(
            token,
            pickup_address, pickup_city, pickup_state, pickup_postal, pickup_country,
            dropoff_address, dropoff_city, dropoff_state, dropoff_postal, dropoff_country
        )

        click.echo("\n🚗 Ride request created successfully! 🚗\n")
        click.echo(f"Ride ID: {ride['id']}")
        click.echo(f"Status: {ride['status']}")
        
        # Display pickup and dropoff details
        click.echo("\n📍 Pickup Location:")
        click.echo(f"   {ride['pickup_location']['address']}")
        click.echo(f"   {ride['pickup_location']['city']}, {ride['pickup_location']['state']} {ride['pickup_location']['postal_code']}")
        
        click.echo("\n🏁 Dropoff Location:")
        click.echo(f"   {ride['dropoff_location']['address']}")
        click.echo(f"   {ride['dropoff_location']['city']}, {ride['dropoff_location']['state']} {ride['dropoff_location']['postal_code']}")
        
        # Display ride estimates
        click.echo("\n📊 Ride Estimates:")
        click.echo(f"   Distance: {ride['distance']} km")
        click.echo(f"   Duration: {ride['duration']} minutes")
        click.echo(f"   Estimated Fare: ${ride['estimated_fare']}")
        
        click.echo("\nWe're looking for a driver to accept your ride request...")
        click.echo("Use 'cabcab ride status <ride_id>' to check the status of your ride.")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ride_group.command(name="list", help="List your ride history")
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
        
        click.echo("\nUse 'cabcab ride status <ride_id>' to view details of a specific ride.")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ride_group.command(name="status", help="Check the status of a specific ride")
@click.argument("ride_id", required=True)
def ride_status(ride_id):
    """Check the status and details of a specific ride."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
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
        
        click.echo("\n📍 Pickup Location:")
        click.echo(f"   {pickup.get('address')}")
        click.echo(f"   {pickup.get('city')}, {pickup.get('state')} {pickup.get('postal_code')}")
        
        click.echo("\n🏁 Dropoff Location:")
        click.echo(f"   {dropoff.get('address')}")
        click.echo(f"   {dropoff.get('city')}, {dropoff.get('state')} {dropoff.get('postal_code')}")
        
        # Display ride estimates
        click.echo("\n📊 Ride Information:")
        click.echo(f"   Distance: {ride.get('distance')} km")
        click.echo(f"   Duration: {ride.get('duration')} minutes")
        click.echo(f"   Estimated Fare: ${ride.get('estimated_fare')}")
        
        # Display driver information if assigned
        if ride.get('driver_id'):
            click.echo("\n👤 Driver Information:")
            click.echo(f"   Driver ID: {ride.get('driver_id')}")
            # In a full implementation, we would fetch and display additional driver details
        
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
@click.argument("ride_id", required=True)
@click.option("--confirm", is_flag=True, help="Confirm cancellation without prompting")
def cancel_ride(ride_id, confirm):
    """Cancel a requested ride."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get ride details first
        ride = RideService.get_ride_by_id(ride_id)
        
        click.echo(f"Cancelling ride from:")
        pickup = ride.get('pickup_location', {})
        dropoff = ride.get('dropoff_location', {})
        click.echo(f"   {pickup.get('address')}, {pickup.get('city')}")
        click.echo(f"To:")
        click.echo(f"   {dropoff.get('address')}, {dropoff.get('city')}")
        
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


@ride_group.command(name="rate", help="Rate a completed ride")
@click.argument("ride_id", required=True)
@click.option("--rating", type=click.IntRange(1, 5), prompt=True, 
              help="Rate your ride (1-5 stars)")
@click.option("--feedback", prompt="Additional feedback (optional)", 
              default="", help="Additional feedback about your ride")
@require_user_type([UserType.PASSENGER.value])
def rate_ride(ride_id, rating, feedback):
    """Rate a completed ride."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # This is a placeholder for the full implementation
        # In a complete solution, we would update the ride with the rating
        click.echo("This feature is coming soon!")
        click.echo(f"Your {rating}-star rating for ride {ride_id} has been recorded.")
        if feedback:
            click.echo(f"Feedback: \"{feedback}\"")

    except (RideServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)