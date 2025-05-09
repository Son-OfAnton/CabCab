"""Authentication commands for the CabCab CLI."""

from datetime import datetime
import os
import click

from app.services.auth_service import AuthService, AuthError, UserType
from app.cli_module.utils import save_token, get_token


@click.group(name="auth")
def auth_group():
    """Authentication commands."""
    pass


@auth_group.group(name="register")
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
        result = AuthService.register_passenger(email, password, first_name, last_name, phone)
        save_token(result["token"])
        click.echo(f"Passenger {first_name} {last_name} registered successfully!")
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
        result = AuthService.register_driver(email, password, first_name, last_name, phone, license)
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
        result = AuthService.register_admin(email, password, first_name, last_name, phone, code)
        save_token(result["token"])
        click.echo(f"Admin {first_name} {last_name} registered successfully!")
        click.echo(f"Email: {email}")
        click.echo("You are now logged in with admin privileges.")
    except AuthError as e:
        click.echo(f"Error during admin registration: {str(e)}", err=True)


@auth_group.command()
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
            available = "available" if user.get('is_available', False) else "not available"
            verified = "verified" if user.get('is_verified', False) else "not verified"
            click.echo(f"You are logged in as a driver. Status: {verified}, {available} for rides.")
        elif user_type == UserType.ADMIN.value:
            click.echo("You are logged in as an admin.")
        else:
            click.echo("You are now logged in.")
    except AuthError as e:
        click.echo(f"Error during signin: {str(e)}", err=True)


@auth_group.command()
def signout():
    """Log out from the application."""
    config_file = os.path.join(os.path.expanduser("~/.cabcab"), "config.json")
    if os.path.exists(config_file):
        os.remove(config_file)
        click.echo("You have been signed out.")
    else:
        click.echo("You were not signed in.")


@auth_group.command()
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
            click.echo(f"License number: {user.get('license_number', 'Not provided')}")
            click.echo(f"Verification status: {'Verified' if user.get('is_verified', False) else 'Not verified'}")
            click.echo(f"Availability: {'Available' if user.get('is_available', False) else 'Not available'} for rides")
            
            # Add vehicle information
            if user.get('vehicle_id'):
                try:
                    from app.services.vehicle_service import VehicleService
                    vehicle = VehicleService.get_vehicle_by_id(user['vehicle_id'])
                    click.echo(f"Primary vehicle: {vehicle['make']} {vehicle['model']} ({vehicle['license_plate']})")
                except Exception:
                    click.echo(f"Vehicle ID: {user['vehicle_id']} (details not available)")
            else:
                click.echo("No primary vehicle assigned.")
                
            # Show vehicle count
            try:
                from app.services.vehicle_service import VehicleService
                vehicles = VehicleService.get_driver_vehicles(token)
                if vehicles:
                    click.echo(f"Total vehicles: {len(vehicles)}")
                else:
                    click.echo("No vehicles registered. Use 'cabcab vehicle register' to add one.")
            except Exception:
                pass
        
        elif user_type == UserType.ADMIN.value:
            click.echo("Admin privileges: Active")
        
    except AuthError as e:
        click.echo(f"Session error: {str(e)}", err=True)
        click.echo("Please sign in again.")


@auth_group.group()
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
        click.echo("No update information provided. Use the options to specify what to update.")
        click.echo("Example: cabcab auth profile update --first-name \"New Name\"")
        return

    try:
        updated_user = AuthService.update_profile(token, update_data)
        click.echo("Profile updated successfully!")
        click.echo(f"Name: {updated_user['first_name']} {updated_user['last_name']}")
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