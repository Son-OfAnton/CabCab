"""Admin-specific commands for the CabCab CLI."""

from datetime import datetime
import click
import requests

from app.services.auth_service import UserType
from app.cli_module.utils import get_token, require_user_type


@click.group(name="admin", help="Admin specific commands for system management")
def admin_group():
    """Admin specific commands for system management and driver verification."""
    pass


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


from datetime import datetime
import click
import requests

from app.services.auth_service import UserType
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