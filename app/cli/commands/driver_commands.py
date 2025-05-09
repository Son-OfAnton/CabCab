"""Driver-specific commands for the CabCab CLI."""

import click

from app.auth.auth_service import AuthService, AuthError, UserType
from app.cli.utils import get_token, require_user_type


@click.group(name="driver")
def driver_group():
    """Driver specific commands."""
    pass


@driver_group.command()
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
        click.echo(f"You are now {'available' if is_available else 'unavailable'} for ride requests.")
    except AuthError as e:
        click.echo(f"Error setting availability: {str(e)}", err=True)