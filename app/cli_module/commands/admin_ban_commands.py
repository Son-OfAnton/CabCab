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
            click.echo(f"  cabcab admin ban unban {email}")

    except (UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ban_group.command(name="unban")
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


@ban_group.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="Show all users with ban history, not just currently banned")
@require_user_type([UserType.ADMIN.value])
def list_banned_users(show_all):
    """List all banned passengers."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get banned users
        banned_users = UserService.list_banned_passengers(token, not show_all)
        
        if not banned_users:
            status = "banned" if not show_all else "with ban history"
            click.echo(f"There are no passengers currently {status}.")
            return
        
        # Prepare data for table
        table_data = []
        for user in banned_users:
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
                status = "PERMANENT" if user.get('is_permanent_ban') else "TEMPORARY"
            else:
                status = "UNBANNED"
                
            table_data.append([
                user.get('id'),
                f"{user.get('first_name', '')} {user.get('last_name', '')}",
                user.get('email'),
                status,
                ban_date,
                user.get('ban_reason') or "N/A"
            ])
        
        # Print banned users
        title = "Currently Banned Passengers" if not show_all else "All Passengers with Ban History"
        click.echo(f"\n⛔ {title}:\n")
        click.echo(tabulate(
            table_data,
            headers=["ID", "Name", "Email", "Status", "Ban Date", "Reason"],
            tablefmt="grid"
        ))
        
        # Show instructions
        click.echo("\nTo unban a passenger, use:")
        click.echo("  cabcab admin ban unban <email>")

    except (UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@ban_group.command(name="status")
@click.argument("email", metavar="EMAIL")
@require_user_type([UserType.ADMIN.value])
def check_ban_status(email):
    """
    Check the ban status for a specific passenger.
    
    EMAIL: The email address of the passenger to check.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Find the user first
        from app.services.auth_service import AuthService
        import requests
        
        # Find user by email
        response = requests.get(f"http://localhost:3000/users/query?email={email}")
        
        if response.status_code == 404 or not response.json():
            click.echo(f"User with email {email} not found", err=True)
            return
        
        user = response.json()[0]
        
        # Check if user is a passenger
        if user.get('user_type') != UserType.PASSENGER.value:
            click.echo(f"User with email {email} is not a passenger", err=True)
            return
        
        # Get ban status
        ban_status = UserService.get_ban_status(user['id'])
        
        click.echo(f"\nBan status for: {user.get('first_name', '')} {user.get('last_name', '')} ({email})")
        
        if ban_status.get('is_banned'):
            # User is banned
            ban_type = "PERMANENT" if ban_status.get('is_permanent') else "TEMPORARY"
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
            click.echo(f"Reason: {ban_status.get('reason') or 'No reason provided'}")
            
            if ban_status.get('banned_by_email'):
                click.echo(f"Banned by: {ban_status.get('banned_by_email')}")
                
            # Show unban option
            click.echo("\nTo unban this passenger, use:")
            click.echo(f"  cabcab admin ban unban {email}")
        else:
            # User is not banned
            click.echo("Status: ✅ NOT BANNED")
            
            # Check if they have ban history
            if user.get('banned_at') or user.get('unbanned_at'):
                click.echo("Note: This passenger has previous ban history.")

    except (UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)