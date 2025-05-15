"""Admin-specific commands for the CabCab CLI."""

from datetime import datetime
import click
import requests

from app.services.auth_service import UserType
from app.services.user_service import UserService, UserServiceError
from app.cli_module.utils import get_token, require_user_type
from app.cli_module.commands.admin_ban_commands import ban_group


@click.group(name="admin", help="Admin specific commands for system management")
def admin_group():
    """Admin specific commands for system management and driver verification."""
    pass


# Add the ban commands as a subgroup
admin_group.add_command(ban_group)


@admin_group.command(name="verify_driver", help="Verify or unverify a driver account by email.")
@click.argument('email', metavar="EMAIL")
@click.option("--verify/--unverify", required=True,
              help="Set to --verify to verify the driver or --unverify to remove verification")
@require_user_type([UserType.ADMIN.value])
def verify_driver(email, verify):
    """
    Verify or unverify a driver's account.

    EMAIL: The email address of the driver to verify or unverify.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Find the user by email
        response = requests.get(f"http://localhost:3000/users/query?email={email}")
        
        if response.status_code == 404:
            click.echo(f"No user found with email {email}", err=True)
            return

        response.raise_for_status()
        users = response.json()
        
        if not users:
            click.echo(f"No user found with email {email}", err=True)
            return
            
        # Get the first user with the specified email
        user = users[0]
        
        # Check if user is a driver
        if user.get('user_type') != UserType.DRIVER.value:
            click.echo(f"User with email {email} is not a driver.", err=True)
            return

        # Update verification status
        user['is_verified'] = verify
        user['updated_at'] = datetime.now().isoformat()

        # Save the updated user
        response = requests.put(
            f"http://localhost:3000/users/{user['id']}", json=user)
        response.raise_for_status()

        verification_status = 'verified' if verify else 'unverified'
        click.echo(
            f"Driver {user['first_name']} {user['last_name']} ({email}) has been {verification_status}.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@admin_group.command(name="driver-info", help="View contact information of a driver by ID or email.")
@click.option('--id', 'driver_id', help='Driver ID')
@click.option('--email', help='Driver email')
@require_user_type([UserType.ADMIN.value])
def driver_info(driver_id, email):
    """
    View detailed contact information of a driver by ID or email.
    
    Requires admin privileges.
    """
    if not driver_id and not email:
        click.echo("Error: You must provide either --id or --email", err=True)
        return
    
    token = get_token()
    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return
    
    try:
        # Use the service to get driver information
        driver_data = UserService.get_driver_info(token, driver_id, email)
        
        # Extract the data
        user = driver_data['user']
        driver = driver_data['driver']
        vehicle = driver_data['vehicle']
        
        # Display the contact information
        click.echo(f"\n--- Driver Contact Information ---")
        click.echo(f"ID: {user['id']}")
        click.echo(f"Name: {user['first_name']} {user['last_name']}")
        click.echo(f"Email: {user['email']}")
        click.echo(f"Phone: {user['phone']}")
        
        # Add driver-specific information if available
        if 'license_number' in driver:
            click.echo(f"License Number: {driver['license_number']}")
        
        if user.get('is_verified'):
            click.echo(f"Verification Status: Verified")
        else:
            click.echo(f"Verification Status: Not Verified")
            
        if driver.get('is_active'):
            click.echo(f"Account Status: Active")
        else:
            click.echo(f"Account Status: Inactive")
            
        if driver.get('rating'):
            click.echo(f"Rating: {driver['rating']}/5.0")
        else:
            click.echo(f"Rating: Not rated yet")
            
        # Show vehicle information if available
        if vehicle:
            click.echo("\n--- Vehicle Information ---")
            click.echo(f"Vehicle: {vehicle.get('year', 'N/A')} {vehicle.get('make', 'N/A')} {vehicle.get('model', 'N/A')}")
            click.echo(f"Color: {vehicle.get('color', 'N/A')}")
            click.echo(f"License Plate: {vehicle.get('license_plate', 'N/A')}")
            click.echo(f"Type: {vehicle.get('vehicle_type', 'N/A')}")
            click.echo(f"Capacity: {vehicle.get('capacity', 'N/A')} passengers")
                
    except UserServiceError as e:
        click.echo(f"Error: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)