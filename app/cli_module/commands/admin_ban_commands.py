"""Admin ban commands for the CabCab CLI."""

import click
from tabulate import tabulate
from datetime import datetime

from app.services.user_service import UserService, UserServiceError
from app.services.auth_service import AuthError, UserType
from app.cli_module.utils import get_token, require_user_type


@click.group(name="ban")
def ban_group():
    """User banning and unbanning commands."""
    pass


@ban_group.command(name="passenger")
@click.argument("email", metavar="EMAIL")
@click.option("--reason", prompt="Reason for ban", help="Reason for banning the passenger")
@click.option("--permanent", is_flag=True, help="If set, the ban will be permanent")
@require_user_type([UserType.ADMIN.value])
def ban_passenger(email, reason, permanent):
    """
    Ban a passenger from using the service.
    
    EMAIL: The email address of the passenger to ban.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Display ban confirmation before proceeding
        ban_type = "permanently" if permanent else "temporarily"
        if not click.confirm(f"Are you sure you want to {ban_type} ban passenger {email}?"):
            click.echo("Ban operation cancelled.")
            return
            
        # Ban the passenger
        banned_user = UserService.ban_passenger(token, email, reason, permanent)
        
        # Display success message
        ban_type = "PERMANENT" if permanent else "TEMPORARY"
        click.echo(f"\n⛔ Passenger {banned_user['first_name']} {banned_user['last_name']} ({email}) has been BANNED.")
        click.echo(f"Ban type: {ban_type}")
        click.echo(f"Reason: {reason}")
        click.echo(f"Ban time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show instructions for unbanning
        if not permanent:
            click.echo("\nTo unban this passenger in the future, use:")
            click.echo(f"  cabcab admin ban unban-passenger {email}")

    except (UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ban_group.command(name="driver")
@click.argument("email", metavar="EMAIL")
@click.option("--reason", prompt="Reason for ban", help="Reason for banning the driver")
@click.option("--permanent", is_flag=True, help="If set, the ban will be permanent")
@require_user_type([UserType.ADMIN.value])
def ban_driver(email, reason, permanent):
    """
    Ban a driver from using the service.
    
    EMAIL: The email address of the driver to ban.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Display ban confirmation before proceeding
        ban_type = "permanently" if permanent else "temporarily"
        if not click.confirm(f"Are you sure you want to {ban_type} ban driver {email}?"):
            click.echo("Ban operation cancelled.")
            return
            
        # Ban the driver
        banned_user = UserService.ban_driver(token, email, reason, permanent)
        
        # Display success message
        ban_type = "PERMANENT" if permanent else "TEMPORARY"
        click.echo(f"\n⛔ Driver {banned_user['first_name']} {banned_user['last_name']} ({email}) has been BANNED.")
        click.echo(f"Ban type: {ban_type}")
        click.echo(f"Reason: {reason}")
        click.echo(f"Ban time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show instructions for unbanning
        if not permanent:
            click.echo("\nTo unban this driver in the future, use:")
            click.echo(f"  cabcab admin ban unban-driver {email}")

    except (UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ban_group.command(name="unban-passenger")
@click.argument("email", metavar="EMAIL")
@require_user_type([UserType.ADMIN.value])
def unban_passenger(email):
    """
    Unban a previously banned passenger.
    
    EMAIL: The email address of the passenger to unban.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Confirm unban operation
        if not click.confirm(f"Are you sure you want to unban passenger {email}?"):
            click.echo("Unban operation cancelled.")
            return
            
        # Unban the passenger
        unbanned_user = UserService.unban_passenger(token, email)
        
        # Display success message
        click.echo(f"\n✅ Passenger {unbanned_user['first_name']} {unbanned_user['last_name']} ({email}) has been UNBANNED.")
        click.echo(f"Unban time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except (UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ban_group.command(name="unban-driver")
@click.argument("email", metavar="EMAIL")
@require_user_type([UserType.ADMIN.value])
def unban_driver(email):
    """
    Unban a previously banned driver.
    
    EMAIL: The email address of the driver to unban.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Confirm unban operation
        if not click.confirm(f"Are you sure you want to unban driver {email}?"):
            click.echo("Unban operation cancelled.")
            return
            
        # Unban the driver
        unbanned_user = UserService.unban_driver(token, email)
        
        # Display success message
        click.echo(f"\n✅ Driver {unbanned_user['first_name']} {unbanned_user['last_name']} ({email}) has been UNBANNED.")
        click.echo(f"Unban time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except (UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ban_group.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="Show all users with ban history, not just currently banned")
@click.option("--type", "user_type", type=click.Choice(['all', 'passengers', 'drivers']), default='all',
              help="Filter list by user type (all, passengers, drivers)")
@require_user_type([UserType.ADMIN.value])
def list_banned_users(show_all, user_type):
    """List all banned users (passengers and/or drivers)."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get banned users based on type
        all_banned_users = []
        
        if user_type in ['all', 'passengers']:
            banned_passengers = UserService.list_banned_passengers(token, not show_all)
            for user in banned_passengers:
                user['user_type_display'] = "Passenger"
            all_banned_users.extend(banned_passengers)
        
        if user_type in ['all', 'drivers']:
            banned_drivers = UserService.list_banned_drivers(token, not show_all)
            for user in banned_drivers:
                user['user_type_display'] = "Driver"
            all_banned_users.extend(banned_drivers)
        
        if not all_banned_users:
            status = "banned" if not show_all else "with ban history"
            type_filter = "" if user_type == 'all' else f"{user_type} "
            click.echo(f"There are no {type_filter}currently {status}.")
            return
        
        # Prepare data for table
        table_data = []
        for user in all_banned_users:
            # Format the ban date
            ban_date = None
            if user.get('banned_at'):
                try:
                    dt = datetime.fromisoformat(user['banned_at'].replace('Z', '+00:00'))
                    ban_date = dt.strftime('%Y-%m-%d %H:%M')
                except (ValueError, TypeError):
                    ban_date = user.get('banned_at')
            
            # Format status
            if user.get('is_banned'):
                status = "PERMANENT" if user.get('permanent_ban') else "TEMPORARY"
            else:
                status = "UNBANNED"
                
            # Additional driver-specific info
            additional_info = ""
            if user.get('user_type') == UserType.DRIVER.value:
                if user.get('license_number'):
                    additional_info = f"License: {user.get('license_number')}"
                elif user.get('license_plate'):
                    additional_info = f"Plate: {user.get('license_plate')}"
                
            table_data.append([
                user.get('id'),
                f"{user.get('first_name', '')} {user.get('last_name', '')}",
                user.get('email'),
                user.get('user_type_display', 'Unknown'),
                status,
                ban_date,
                user.get('banned_reason') or "N/A",
                additional_info
            ])
        
        # Print banned users
        filter_text = " " if user_type == 'all' else f" {user_type.title()} "
        title = f"Currently Banned{filter_text}Users" if not show_all else f"All{filter_text}Users with Ban History"
        click.echo(f"\n⛔ {title}:\n")
        click.echo(tabulate(
            table_data,
            headers=["ID", "Name", "Email", "Type", "Status", "Ban Date", "Reason", "Additional Info"],
            tablefmt="grid"
        ))
        
        # Show instructions
        click.echo("\nTo unban a user, use one of the following:")
        click.echo("  cabcab admin ban unban-passenger <email>   # For passengers")
        click.echo("  cabcab admin ban unban-driver <email>      # For drivers")

    except (UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ban_group.command(name="status-passenger")
@click.argument("email", metavar="EMAIL")
@require_user_type([UserType.ADMIN.value])
def check_passenger_ban_status(email):
    """
    Check the ban status for a specific passenger.
    
    EMAIL: The email address of the passenger to check.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get ban status
        ban_status = UserService.get_ban_status(token, email)
        
        click.echo(f"\nBan status for passenger: {ban_status.get('name')} ({email})")
        
        if ban_status.get('is_banned'):
            # User is banned
            ban_type = "PERMANENT" if ban_status.get('permanent_ban') else "TEMPORARY"
            click.echo(f"Status: ⛔ BANNED ({ban_type})")
            
            # Format ban date
            ban_date = "Unknown"
            if ban_status.get('banned_at'):
                try:
                    dt = datetime.fromisoformat(ban_status.get('banned_at').replace('Z', '+00:00'))
                    ban_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    ban_date = ban_status.get('banned_at')
                    
            click.echo(f"Banned since: {ban_date}")
            click.echo(f"Reason: {ban_status.get('banned_reason') or 'No reason provided'}")
            
            if ban_status.get('banned_by_email'):
                click.echo(f"Banned by: {ban_status.get('banned_by_email')}")
                
            # Show unban option
            click.echo("\nTo unban this passenger, use:")
            click.echo(f"  cabcab admin ban unban-passenger {email}")
        else:
            # User is not banned
            click.echo("Status: ✅ NOT BANNED")
            
            # Check if they have ban history
            if ban_status.get('previously_banned'):
                click.echo("Note: This passenger has previous ban history.")

    except (UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ban_group.command(name="status-driver")
@click.argument("email", metavar="EMAIL")
@require_user_type([UserType.ADMIN.value])
def check_driver_ban_status(email):
    """
    Check the ban status for a specific driver.
    
    EMAIL: The email address of the driver to check.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get ban status
        ban_status = UserService.get_driver_ban_status(token, email)
        
        click.echo(f"\nBan status for driver: {ban_status.get('name')} ({email})")
        
        if ban_status.get('is_banned'):
            # Driver is banned
            ban_type = "PERMANENT" if ban_status.get('permanent_ban') else "TEMPORARY"
            click.echo(f"Status: ⛔ BANNED ({ban_type})")
            
            # Format ban date
            ban_date = "Unknown"
            if ban_status.get('banned_at'):
                try:
                    dt = datetime.fromisoformat(ban_status.get('banned_at').replace('Z', '+00:00'))
                    ban_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    ban_date = ban_status.get('banned_at')
                    
            click.echo(f"Banned since: {ban_date}")
            click.echo(f"Reason: {ban_status.get('banned_reason') or 'No reason provided'}")
            
            if ban_status.get('banned_by_name'):
                click.echo(f"Banned by: {ban_status.get('banned_by_name')} ({ban_status.get('banned_by_email')})")
                
            # Show unban option
            click.echo("\nTo unban this driver, use:")
            click.echo(f"  cabcab admin ban unban-driver {email}")
        else:
            # Driver is not banned
            click.echo("Status: ✅ NOT BANNED")
            
            # Check if they have ban history
            if ban_status.get('previously_banned'):
                click.echo("Note: This driver has previous ban history.")
                
                # If unbanned, show unban date and who unbanned them
                if ban_status.get('unbanned_at'):
                    try:
                        dt = datetime.fromisoformat(ban_status.get('unbanned_at').replace('Z', '+00:00'))
                        unban_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        unban_date = ban_status.get('unbanned_at')
                        
                    click.echo(f"Unbanned on: {unban_date}")
                    
                    if ban_status.get('unbanned_by_name'):
                        click.echo(f"Unbanned by: {ban_status.get('unbanned_by_name')}")

    except (UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


# Backward compatibility commands - these redirect to the new specific commands
@ban_group.command(name="unban", help="Unban a previously banned passenger (Legacy command)")
@click.argument("email", metavar="EMAIL")
@require_user_type([UserType.ADMIN.value])
def unban_legacy(email):
    """Legacy command that redirects to unban-passenger."""
    click.echo("Note: 'ban unban' is deprecated. Please use 'ban unban-passenger' or 'ban unban-driver' instead.\n")
    ctx = click.get_current_context()
    ctx.forward(unban_passenger)


@ban_group.command(name="status", help="Check ban status for a passenger (Legacy command)")
@click.argument("email", metavar="EMAIL")
@require_user_type([UserType.ADMIN.value])
def status_legacy(email):
    """Legacy command that redirects to status-passenger."""
    click.echo("Note: 'ban status' is deprecated. Please use 'ban status-passenger' or 'ban status-driver' instead.\n")
    ctx = click.get_current_context()
    ctx.forward(check_passenger_ban_status)