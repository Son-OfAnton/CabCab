"""
Admin commission commands for the CabCab CLI.

This module implements commands for admins to manage commission settings
and view commission earnings from rides.
"""

import click
from tabulate import tabulate
from datetime import datetime

from app.services.commision_service import CommissionService, CommissionServiceError
from app.services.auth_service import AuthError, UserType
from app.cli_module.utils import get_token, require_user_type


@click.group(name="commission")
def commission_group():
    """Commission management commands."""
    pass


@commission_group.command(name="set")
@click.option("--payment-method", required=True, help="ID of payment method to receive commissions")
@click.option("--percentage", type=float, default=10.0, help="Commission percentage (default: 10%)")
@require_user_type([UserType.ADMIN.value])
def set_commission(payment_method, percentage):
    """Set up or update commission settings."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        settings = CommissionService.set_admin_commission(
            token, payment_method, percentage
        )

        click.echo("\n✅ Commission settings updated successfully!\n")
        
        # Display commission settings
        click.echo(f"Commission percentage: {settings['percentage']}%")
        click.echo(f"Payment method ID: {settings['payment_method_id']}")
        click.echo(f"Status: {'Active' if settings['is_active'] else 'Inactive'}")
        
        if not settings['is_active']:
            click.echo("\nTip: Use 'cabcab admin commission enable' to start collecting commissions.")
        else:
            click.echo("\nCommissions will be automatically collected from all future rides.")

    except (CommissionServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@commission_group.command(name="status")
@require_user_type([UserType.ADMIN.value])
def commission_status():
    """View commission configuration and earnings."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get commission data
        commission_data = CommissionService.get_admin_commission(token)

        if not commission_data['settings']:
            click.echo("Commission is not configured yet.")
            click.echo("Use 'cabcab admin commission set --payment-method PAYMENT_ID' to set up commission.")
            return

        settings = commission_data['settings']
        statistics = commission_data['statistics']

        # Display commission settings
        click.echo("\n💰 Commission Settings:")
        click.echo(f"Percentage: {settings['percentage']}%")
        click.echo(f"Status: {'✅ Active' if settings['is_active'] else '❌ Inactive'}")
        
        if 'payment_method' in settings and settings['payment_method']:
            payment_method = settings['payment_method']
            click.echo(f"Payment Method: {payment_method.get('display_name', payment_method.get('id'))}")

        # Display commission statistics
        click.echo("\n📊 Commission Statistics:")
        click.echo(f"Total earnings: ${statistics['total_earned']:.2f}")
        click.echo(f"Total rides with commission: {statistics['ride_count']}")

        # Display recent transactions
        recent = statistics['recent_transactions']
        if recent:
            click.echo("\nRecent Commission Transactions:")
            
            table_data = []
            for tx in recent:
                # Format date
                created_at = "Unknown"
                if tx.get('created_at'):
                    try:
                        dt = datetime.fromisoformat(tx['created_at'].replace('Z', '+00:00'))
                        created_at = dt.strftime('%Y-%m-%d %H:%M')
                    except (ValueError, TypeError):
                        created_at = tx.get('created_at')
                
                # Get ride info
                ride_info = "N/A"
                if 'ride' in tx and tx['ride']:
                    ride = tx['ride']
                    ride_id = ride.get('id', 'Unknown')[:8]
                    amount = ride.get('actual_fare', 0.0)
                    ride_info = f"Ride {ride_id}... (${amount:.2f})"
                
                table_data.append([
                    created_at,
                    f"${tx.get('amount', 0.0):.2f}",
                    ride_info,
                    tx.get('status', 'UNKNOWN')
                ])

            click.echo(tabulate(
                table_data,
                headers=["Date", "Commission", "Ride", "Status"],
                tablefmt="pretty"
            ))

    except (CommissionServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@commission_group.command(name="enable")
@require_user_type([UserType.ADMIN.value])
def enable_commission():
    """Enable commission collection."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        settings = CommissionService.enable_admin_commission(token)
        
        click.echo("\n✅ Commission collection is now enabled!")
        click.echo(f"\nCommission percentage: {settings['percentage']}%")
        click.echo(f"Payment method ID: {settings['payment_method_id']}")
        click.echo("\nCommissions will be automatically collected from all future rides.")

    except (CommissionServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@commission_group.command(name="disable")
@require_user_type([UserType.ADMIN.value])
def disable_commission():
    """Disable commission collection."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        settings = CommissionService.disable_admin_commission(token)
        
        click.echo("\n✅ Commission collection has been disabled.")
        click.echo("\nNo commissions will be collected from future rides until you enable it again.")
        click.echo("Use 'cabcab admin commission enable' to re-enable commission collection.")

    except (CommissionServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)