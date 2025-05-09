"""Command Line Interface for CabCab application."""

from datetime import datetime
import os
import click
import json

import requests
from app.main import process_command
from app.auth.auth_service import AuthService, AuthError, UserType
from app.services.vehicle_service import VehicleService, VehicleServiceError

# Config file to store auth token
CONFIG_DIR = os.path.expanduser("~/.cabcab")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def save_token(token: str) -> None:
    """Save auth token to config file."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    with open(CONFIG_FILE, 'w') as f:
        json.dump({"token": token}, f)


def get_token() -> str:
    """Get auth token from config file."""
    if not os.path.exists(CONFIG_FILE):
        return None

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get("token")
    except json.JSONDecodeError:
        return None


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    token = get_token()

    if not token:
        return False

    try:
        AuthService.verify_token(token)
        return True
    except AuthError:
        return False


def require_user_type(required_types):
    """Decorator to require specific user types."""
    def decorator(f):
        def wrapped(*args, **kwargs):
            token = get_token()
            if not token:
                click.echo(
                    "You are not signed in. Please sign in first.", err=True)
                return

            try:
                AuthService.require_user_type(token, required_types)
                return f(*args, **kwargs)
            except AuthError as e:
                click.echo(f"Access denied: {str(e)}", err=True)
                return
        return wrapped
    return decorator


@click.group()
def cli():
    """CabCab CLI application."""
    pass


@cli.group()
def auth():
    """Authentication commands."""
    pass


@auth.group(name="register")
def register_group():
    """Register a new user."""
    pass


@register_group.command(name="passenger")
@click.option("--email", prompt=True, help="Your email address")
@click.option("--password", prompt=True, hide_input=True, help="Your password")
@click.option("--first-name", prompt=True, help="Your first name")
@click.option("--last-name", prompt=True, help="Your last name")
@click.option("--phone", prompt=True, help="Your phone number")
def register_passenger(email, password, first_name, last_name, phone):
    """Register as a passenger."""
    try:
        result = AuthService.register_passenger(
            email, password, first_name, last_name, phone)
        save_token(result["token"])
        click.echo(
            f"Passenger {first_name} {last_name} registered successfully!")
        click.echo(f"Email: {email}")
        click.echo("You are now logged in.")
    except AuthError as e:
        click.echo(f"Error during registration: {str(e)}", err=True)


@register_group.command(name="driver")
@click.option("--email", prompt=True, help="Your email address")
@click.option("--password", prompt=True, hide_input=True, help="Your password")
@click.option("--first-name", prompt=True, help="Your first name")
@click.option("--last-name", prompt=True, help="Your last name")
@click.option("--phone", prompt=True, help="Your phone number")
@click.option("--license", prompt=True, help="Your driver's license number")
def register_driver(email, password, first_name, last_name, phone, license):
    """Register as a driver."""
    try:
        result = AuthService.register_driver(
            email, password, first_name, last_name, phone, license)
        save_token(result["token"])
        click.echo(f"Driver {first_name} {last_name} registered successfully!")
        click.echo(f"Email: {email}")
        click.echo("Your account requires verification before accepting rides.")
        click.echo("You are now logged in.")
    except AuthError as e:
        click.echo(f"Error during registration: {str(e)}", err=True)


@register_group.command(name="admin")
@click.option("--email", prompt=True, help="Admin email address")
@click.option("--password", prompt=True, hide_input=True, help="Admin password")
@click.option("--first-name", prompt=True, help="Admin first name")
@click.option("--last-name", prompt=True, help="Admin last name")
@click.option("--phone", prompt=True, help="Admin phone number")
@click.option("--code", prompt=True, hide_input=True, help="Admin registration code")
def register_admin(email, password, first_name, last_name, phone, code):
    """Register as an admin (requires authorization code)."""
    try:
        result = AuthService.register_admin(
            email, password, first_name, last_name, phone, code)
        save_token(result["token"])
        click.echo(f"Admin {first_name} {last_name} registered successfully!")
        click.echo(f"Email: {email}")
        click.echo("You are now logged in with admin privileges.")
    except AuthError as e:
        click.echo(f"Error during admin registration: {str(e)}", err=True)


@auth.command()
@click.option("--email", prompt=True, help="Your email address")
@click.option("--password", prompt=True, hide_input=True, help="Your password")
def signin(email, password):
    """Log in with credentials."""
    try:
        result = AuthService.login(email, password)
        save_token(result["token"])
        user = result["user"]
        click.echo(f"Welcome back, {user['first_name']} {user['last_name']}!")

        # Display different messages based on user type
        user_type = user.get('user_type')
        if user_type == UserType.PASSENGER.value:
            click.echo("You are logged in as a passenger.")
        elif user_type == UserType.DRIVER.value:
            available = "available" if user.get(
                'is_available', False) else "not available"
            verified = "verified" if user.get(
                'is_verified', False) else "not verified"
            click.echo(
                f"You are logged in as a driver. Status: {verified}, {available} for rides.")
        elif user_type == UserType.ADMIN.value:
            click.echo("You are logged in as an admin.")
        else:
            click.echo("You are now logged in.")
    except AuthError as e:
        click.echo(f"Error during signin: {str(e)}", err=True)


@auth.command()
def signout():
    """Log out from the application."""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        click.echo("You have been signed out.")
    else:
        click.echo("You were not signed in.")


@auth.command()
def whoami():
    """Show current user information."""
    token = get_token()

    if not token:
        click.echo("You are not signed in.", err=True)
        return

    try:
        user = AuthService.verify_token(token)
        user_type = user.get('user_type')

        # Basic user info for all user types
        click.echo(f"Signed in as: {user['first_name']} {user['last_name']}")
        click.echo(f"Email: {user['email']}")
        click.echo(f"Phone: {user['phone']}")
        click.echo(f"User Type: {user_type.capitalize()}")
        if user.get('rating'):
            click.echo(f"Rating: {user['rating']}")
        click.echo(f"Account created: {user['created_at']}")
        click.echo(f"Last updated: {user['updated_at']}")

        # Type-specific information
        if user_type == UserType.PASSENGER.value:
            payment_methods = len(user.get('payment_methods', []))
            click.echo(f"Payment methods: {payment_methods}")

        elif user_type == UserType.DRIVER.value:
            click.echo(
                f"License number: {user.get('license_number', 'Not provided')}")
            click.echo(
                f"Verification status: {'Verified' if user.get('is_verified', False) else 'Not verified'}")
            click.echo(
                f"Availability: {'Available' if user.get('is_available', False) else 'Not available'} for rides")
            if user.get('vehicle_id'):
                click.echo(f"Vehicle ID: {user['vehicle_id']}")
            else:
                click.echo("No vehicle assigned.")

        elif user_type == UserType.ADMIN.value:
            click.echo("Admin privileges: Active")

    except AuthError as e:
        click.echo(f"Session error: {str(e)}", err=True)
        click.echo("Please sign in again.")


@auth.group()
def profile():
    """Manage your profile."""
    pass


@profile.command()
@click.option("--first-name", help="Update your first name")
@click.option("--last-name", help="Update your last name")
@click.option("--phone", help="Update your phone number")
def update(first_name, last_name, phone):
    """Update your profile information."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    # Collect update data
    update_data = {}
    if first_name:
        update_data['first_name'] = first_name
    if last_name:
        update_data['last_name'] = last_name
    if phone:
        update_data['phone'] = phone

    if not update_data:
        click.echo(
            "No update information provided. Use the options to specify what to update.")
        click.echo(
            "Example: cabcab auth profile update --first-name \"New Name\"")
        return

    try:
        updated_user = AuthService.update_profile(token, update_data)
        click.echo("Profile updated successfully!")
        click.echo(
            f"Name: {updated_user['first_name']} {updated_user['last_name']}")
        click.echo(f"Phone: {updated_user['phone']}")
        click.echo(f"Last updated: {updated_user['updated_at']}")
    except AuthError as e:
        click.echo(f"Error updating profile: {str(e)}", err=True)


@profile.command()
@click.option("--current", prompt=True, hide_input=True, help="Current password")
@click.option("--new", prompt=True, hide_input=True, confirmation_prompt=True, help="New password")
def change_password(current, new):
    """Change your password."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        AuthService.change_password(token, current, new)
        click.echo("Password changed successfully!")
    except AuthError as e:
        click.echo(f"Error changing password: {str(e)}", err=True)


@cli.group()
def driver():
    """Driver specific commands."""
    pass


@driver.command()
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


@cli.group()
def admin():
    """Admin specific commands."""
    pass


@admin.command()
@click.argument('user_id')
@click.option("--verify/--unverify", required=True, help="Verify or unverify a driver")
@require_user_type([UserType.ADMIN.value])
def verify_driver(user_id, verify):
    """Verify or unverify a driver."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get the driver
        response = requests.get(f"http://localhost:3000/users/{user_id}")

        if response.status_code == 404:
            click.echo(f"No user found with ID {user_id}", err=True)
            return

        response.raise_for_status()
        user = response.json()

        # Check if user is a driver
        if user.get('user_type') != UserType.DRIVER.value:
            click.echo("The specified user is not a driver.", err=True)
            return

        # Update verification status
        user['is_verified'] = verify
        user['updated_at'] = datetime.now().isoformat()

        # Save the updated user
        response = requests.put(
            f"http://localhost:3000/users/{user_id}", json=user)
        response.raise_for_status()

        click.echo(
            f"Driver {user['first_name']} {user['last_name']} has been {'verified' if verify else 'unverified'}.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@cli.command()
@click.argument('command', required=True)
@click.option('--option', '-o', help='Optional parameter.')
def run(command, option):
    """Execute a CabCab command."""
    # Check if authenticated (except for help/version commands)
    if command not in ['help', 'version'] and not is_authenticated():
        click.echo(
            "You need to sign in first. Use 'cabcab auth signin' to log in.", err=True)
        return

    result = process_command(command, option)
    click.echo(result)


@cli.group()
def vehicle():
    """Vehicle management commands."""
    pass


@vehicle.command()
@click.option("--make", prompt=True, help="Vehicle manufacturer")
@click.option("--model", prompt=True, help="Vehicle model")
@click.option("--year", prompt=True, type=int, help="Vehicle year")
@click.option("--color", prompt=True, help="Vehicle color")
@click.option("--license-plate", prompt=True, help="Vehicle license plate number")
@click.option("--type", "vehicle_type", prompt=True,
              type=click.Choice(
                  ['ECONOMY', 'COMFORT', 'PREMIUM', 'SUV', 'XL'], case_sensitive=False),
              help="Vehicle type")
@click.option("--capacity", prompt=True, type=int, default=4,
              help="Maximum passenger capacity (default: 4)")
@require_user_type([UserType.DRIVER.value])
def register(make, model, year, color, license_plate, vehicle_type, capacity):
    """Register a new vehicle."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        vehicle = VehicleService.register_vehicle(
            token, make, model, year, color, license_plate, vehicle_type, capacity
        )

        click.echo(f"Vehicle registered successfully!")
        click.echo(f"Make: {vehicle['make']}")
        click.echo(f"Model: {vehicle['model']}")
        click.echo(f"Year: {vehicle['year']}")
        click.echo(f"License Plate: {vehicle['license_plate']}")
        click.echo(f"Type: {vehicle['vehicle_type']}")
        click.echo(f"Capacity: {vehicle['capacity']} passengers")
        click.echo(f"Vehicle ID: {vehicle['id']}")

    except (VehicleServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@vehicle.command()
@require_user_type([UserType.DRIVER.value])
def list():
    """List all your vehicles."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        vehicles = VehicleService.get_driver_vehicles(token)

        if not vehicles:
            click.echo("You have no registered vehicles.")
            return

        click.echo(f"You have {len(vehicles)} registered vehicle(s):")

        for i, vehicle in enumerate(vehicles, 1):
            click.echo(f"\nVehicle {i}:")
            click.echo(f"  ID: {vehicle['id']}")
            click.echo(f"  Make: {vehicle['make']}")
            click.echo(f"  Model: {vehicle['model']}")
            click.echo(f"  Year: {vehicle['year']}")
            click.echo(f"  Color: {vehicle['color']}")
            click.echo(f"  License Plate: {vehicle['license_plate']}")
            click.echo(f"  Type: {vehicle['vehicle_type']}")
            click.echo(f"  Capacity: {vehicle['capacity']} passengers")

    except (VehicleServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@vehicle.command()
@click.argument("vehicle_id")
@click.option("--make", help="Update vehicle manufacturer")
@click.option("--model", help="Update vehicle model")
@click.option("--year", type=int, help="Update vehicle year")
@click.option("--color", help="Update vehicle color")
@click.option("--license-plate", help="Update vehicle license plate")
@click.option("--type", "vehicle_type",
              type=click.Choice(
                  ['ECONOMY', 'COMFORT', 'PREMIUM', 'SUV', 'XL'], case_sensitive=False),
              help="Update vehicle type")
@click.option("--capacity", type=int, help="Update maximum passenger capacity")
@click.option("--active/--inactive", default=None, help="Set vehicle active status")
@require_user_type([UserType.DRIVER.value])
def update(vehicle_id, make, model, year, color, license_plate, vehicle_type, capacity, active):
    """Update vehicle information."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    # Collect update data
    update_data = {}
    if make:
        update_data['make'] = make
    if model:
        update_data['model'] = model
    if year:
        update_data['year'] = year
    if color:
        update_data['color'] = color
    if license_plate:
        update_data['license_plate'] = license_plate
    if vehicle_type:
        update_data['vehicle_type'] = vehicle_type
    if capacity:
        update_data['capacity'] = capacity
    if active is not None:
        update_data['is_active'] = active

    if not update_data:
        click.echo(
            "No update information provided. Use the options to specify what to update.")
        click.echo("Example: cabcab vehicle update abc123 --color \"Blue\"")
        return

    try:
        updated_vehicle = VehicleService.update_vehicle(
            token, vehicle_id, update_data)

        click.echo("Vehicle updated successfully!")
        click.echo(f"Make: {updated_vehicle['make']}")
        click.echo(f"Model: {updated_vehicle['model']}")
        click.echo(f"Year: {updated_vehicle['year']}")
        click.echo(f"Color: {updated_vehicle['color']}")
        click.echo(f"License Plate: {updated_vehicle['license_plate']}")
        click.echo(f"Type: {updated_vehicle['vehicle_type']}")
        click.echo(f"Capacity: {updated_vehicle['capacity']} passengers")
        click.echo(
            f"Status: {'Active' if updated_vehicle['is_active'] else 'Inactive'}")

    except (VehicleServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@vehicle.command()
@click.argument("vehicle_id")
@click.option("--confirm", is_flag=True, help="Confirm deletion without prompting")
@require_user_type([UserType.DRIVER.value])
def delete(vehicle_id, confirm):
    """Delete a vehicle."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # First get the vehicle to show details before deleting
        vehicle = VehicleService.get_vehicle_by_id(vehicle_id)

        click.echo(
            f"Vehicle: {vehicle['make']} {vehicle['model']} ({vehicle['year']})")
        click.echo(f"License Plate: {vehicle['license_plate']}")

        # Confirm deletion
        if not confirm and not click.confirm("Are you sure you want to delete this vehicle?"):
            click.echo("Vehicle deletion cancelled.")
            return

        success = VehicleService.delete_vehicle(token, vehicle_id)

        if success:
            click.echo("Vehicle deleted successfully.")
        else:
            click.echo("Failed to delete vehicle.", err=True)

    except (VehicleServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


def main():
    """Entry point for the application."""
    # cli.add_command(vehicle)
    cli()


if __name__ == '__main__':
    main()
