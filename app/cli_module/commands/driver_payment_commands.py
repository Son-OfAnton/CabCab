"""
Driver payment management commands for the CabCab CLI.

This module implements commands for drivers to manage their payment methods
for receiving payments from rides.
"""

import click
from tabulate import tabulate
from datetime import datetime

from app.services.payment_service import PaymentService, PaymentServiceError
from app.services.auth_service import AuthError, UserType
from app.cli_module.utils import get_token, require_user_type


@click.group(name="driver-payment")
def driver_payment_group():
    """Driver payment method management commands."""
    pass


@driver_payment_group.command(name="add")
@click.option("--type", "payment_type", type=click.Choice(['bank-account', 'paypal']), 
              prompt=True, help="Type of payment method to add")
@require_user_type([UserType.DRIVER.value])
def add_driver_payment_method(payment_type):
    """Add a new payment method to receive earnings."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Collect payment details based on type
        payment_details = {}
        
        if payment_type == 'bank-account':
            payment_details["account_holder_name"] = click.prompt("Account holder name")
            payment_details["account_number"] = click.prompt("Account number", hide_input=True)
            payment_details["routing_number"] = click.prompt("Routing number")
            payment_details["bank_name"] = click.prompt("Bank name")
            
            # Normalize payment type for our service
            service_payment_type = "BANK_ACCOUNT"
            
        elif payment_type == 'paypal':
            payment_details["email"] = click.prompt("PayPal email address")
            
            # Normalize payment type for our service
            service_payment_type = "PAYPAL"
        
        # Add the payment method
        payment_method = PaymentService.add_driver_payment_method(
            token, service_payment_type, payment_details
        )

        click.echo("\n✅ Payment method added successfully!\n")
        
        # Display payment method details
        if service_payment_type == "BANK_ACCOUNT":
            click.echo(f"Bank Account: {payment_method['display_name']}")
            click.echo(f"Bank: {payment_method.get('bank_name', 'N/A')}")
        elif service_payment_type == "PAYPAL":
            click.echo(f"PayPal: {payment_method['email']}")
        
        if payment_method.get("is_default"):
            click.echo("This payment method has been set as your default.")

    except (PaymentServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@driver_payment_group.command(name="list")
@require_user_type([UserType.DRIVER.value])
def list_driver_payment_methods():
    """List all your payment methods for receiving earnings."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get all payment methods
        payment_methods = PaymentService.get_driver_payment_methods(token)

        if not payment_methods:
            click.echo("You have no payment methods registered for receiving earnings.")
            click.echo("Use 'cabcab driver-payment add' to add a payment method.")
            return

        # Prepare data for table
        table_data = []
        for method in payment_methods:
            # Format the created date
            created_at = None
            if method.get('created_at'):
                try:
                    dt = datetime.fromisoformat(method['created_at'].replace('Z', '+00:00'))
                    created_at = dt.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    created_at = method.get('created_at')
            
            # Add specific details based on payment type
            details = method.get('display_name', 'Unknown payment method')
            
            # Mark default method
            is_default = "✓" if method.get('is_default') else ""
            
            table_data.append([
                method.get('id'),
                method.get('payment_type'),
                details,
                created_at,
                is_default
            ])

        # Print payment methods
        click.echo("\n💳 Your Earnings Payment Methods:\n")
        click.echo(tabulate(
            table_data,
            headers=["ID", "Type", "Details", "Added On", "Default"],
            tablefmt="pretty"
        ))
        
        click.echo("\nTo set a payment method as default: cabcab driver-payment default <payment_id>")
        click.echo("To remove a payment method: cabcab driver-payment remove <payment_id>")

    except (PaymentServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@driver_payment_group.command(name="default")
@click.argument("payment_id", required=True)
@require_user_type([UserType.DRIVER.value])
def set_default_driver_payment(payment_id):
    """Set a payment method as your default for receiving earnings."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Set the payment method as default
        updated_payment = PaymentService.set_default_driver_payment_method(token, payment_id)
        
        click.echo(f"\n✅ {updated_payment['display_name']} has been set as your default payment method for receiving earnings.")

    except (PaymentServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@driver_payment_group.command(name="remove")
@click.argument("payment_id", required=True)
@click.option("--confirm", is_flag=True, help="Confirm removal without prompting")
@require_user_type([UserType.DRIVER.value])
def remove_driver_payment_method(payment_id, confirm):
    """Remove a payment method for receiving earnings."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get the payment method details first
        methods = PaymentService.get_driver_payment_methods(token)
        payment_method = next((m for m in methods if m["id"] == payment_id), None)
        
        if not payment_method:
            click.echo(f"Payment method with ID {payment_id} not found.", err=True)
            return
            
        # Check for confirmation
        if not confirm:
            is_default = " (your default payment method)" if payment_method.get("is_default") else ""
            
            confirmed = click.confirm(
                f"Are you sure you want to remove {payment_method['display_name']}{is_default}?"
            )
            
            if not confirmed:
                click.echo("Payment method removal cancelled.")
                return
        
        # Remove the payment method
        success = PaymentService.remove_driver_payment_method(token, payment_id)
        
        if success:
            click.echo("\n✅ Payment method removed successfully.")

    except (PaymentServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@driver_payment_group.command(name="history")
@click.option("--limit", type=int, default=10, help="Maximum number of transactions to show")
@click.option("--from-date", type=str, help="Start date (YYYY-MM-DD)")
@click.option("--to-date", type=str, help="End date (YYYY-MM-DD)")
@require_user_type([UserType.DRIVER.value])
def payment_history(limit, from_date, to_date):
    """View your payment history and earnings."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Parse dates if provided
        from_datetime = None
        to_datetime = None
        
        if from_date:
            try:
                from_datetime = datetime.strptime(from_date, "%Y-%m-%d")
                from_datetime = from_datetime.isoformat()
            except ValueError:
                click.echo("Invalid from-date format. Please use YYYY-MM-DD.", err=True)
                return
                
        if to_date:
            try:
                to_datetime = datetime.strptime(to_date, "%Y-%m-%d")
                to_datetime = to_datetime.isoformat()
            except ValueError:
                click.echo("Invalid to-date format. Please use YYYY-MM-DD.", err=True)
                return
        
        # Get payment history
        payment_history = PaymentService.get_driver_payment_history(
            token, limit=limit, from_date=from_datetime, to_date=to_datetime
        )

        if not payment_history["transactions"]:
            click.echo("No payment transactions found for the specified period.")
            return

        # Show summary
        click.echo("\n💰 Payment Summary")
        click.echo(f"Total Earnings: ${payment_history['total_earned']:,.2f}")
        click.echo(f"Pending Amount: ${payment_history['pending_amount']:,.2f}")
        
        if from_date and to_date:
            click.echo(f"Period: {from_date} to {to_date}")
        elif from_date:
            click.echo(f"Period: From {from_date}")
        elif to_date:
            click.echo(f"Period: Until {to_date}")

        # Prepare data for table
        table_data = []
        for transaction in payment_history["transactions"]:
            # Format date
            date = "Unknown"
            if transaction.get('timestamp'):
                try:
                    dt = datetime.fromisoformat(transaction['timestamp'].replace('Z', '+00:00'))
                    date = dt.strftime('%Y-%m-%d %H:%M')
                except (ValueError, TypeError):
                    date = transaction.get('timestamp')
            
            # Format status with color indicators
            status = transaction.get('status', 'UNKNOWN')
            
            # Format ride info
            ride_id = transaction.get('ride_id', 'N/A')
            
            # Add row to table
            table_data.append([
                date,
                f"${transaction.get('amount', 0):,.2f}",
                status,
                transaction.get('payment_method', {}).get('display_name', 'N/A'),
                ride_id
            ])

        # Print transactions
        click.echo("\nRecent Transactions:")
        click.echo(tabulate(
            table_data,
            headers=["Date", "Amount", "Status", "Payment Method", "Ride ID"],
            tablefmt="pretty"
        ))

    except (PaymentServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)