"""Admin-specific commands for the CabCab CLI."""

from datetime import datetime
import click
import requests

from app.auth.auth_service import UserType
from app.cli.utils import get_token, require_user_type


@click.group(name="admin")
def admin_group():
    """Admin specific commands."""
    pass


@admin_group.command()
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
        response = requests.put(f"http://localhost:3000/users/{user_id}", json=user)
        response.raise_for_status()
        
        click.echo(f"Driver {user['first_name']} {user['last_name']} has been {'verified' if verify else 'unverified'}.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)