"""Payment management commands for the CabCab CLI."""

from typing import Optional
import click
from tabulate import tabulate
from datetime import datetime

from app.services.payment_service import PaymentService, PaymentServiceError
from app.services.auth_service import AuthError, UserType
from app.cli_module.utils import get_token, require_user_type


@click.group(name="payment")
def payment_group():
    """Payment method management commands."""
    pass


@payment_group.command(name="add")
@click.option("--type", "payment_type", type=click.Choice(['credit-card', 'paypal']), 
              prompt=True, help="Type of payment method to add")
@require_user_type([UserType.PASSENGER.value])
def add_payment_method(payment_type):
    """Add a new payment method to your account."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Collect payment details based on type
        payment_details = {}
        
        if payment_type == 'credit-card':
            payment_details["card_number"] = click.prompt("Card number", hide_input=False)
            payment_details["expiry_month"] = int(click.prompt("Expiry month (MM)", type=int))
            payment_details["expiry_year"] = int(click.prompt("Expiry year (YYYY)", type=int))
            payment_details["cvv"] = click.prompt("CVV", hide_input=True)
            payment_details["cardholder_name"] = click.prompt("Cardholder name")
            
            # Normalize payment type for our service
            service_payment_type = "CREDIT_CARD"
            
        elif payment_type == 'paypal':
            payment_details["email"] = click.prompt("PayPal email address")
            
            # Normalize payment type for our service
            service_payment_type = "PAYPAL"
        
        # Add the payment method
        payment_method = PaymentService.add_payment_method(
            token, service_payment_type, payment_details
        )

        click.echo("\n✅ Payment method added successfully!\n")
        
        # Display payment method details
        if service_payment_type == "CREDIT_CARD":
            click.echo(f"Card: {payment_method['display_name']}")
            click.echo(f"Expiry: {payment_method['expiry']}")
        elif service_payment_type == "PAYPAL":
            click.echo(f"PayPal: {payment_method['email']}")
        
        if payment_method.get("is_default"):
            click.echo("This payment method has been set as your default.")

    except (PaymentServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@payment_group.command(name="list")
@require_user_type([UserType.PASSENGER.value])
def list_payment_methods():
    """List all your payment methods."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get all payment methods
        payment_methods = PaymentService.get_payment_methods(token)

        if not payment_methods:
            click.echo("You have no payment methods registered.")
            click.echo("Use 'cabcab payment add' to add a payment method.")
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
        click.echo("\n💳 Your Payment Methods:\n")
        click.echo(tabulate(
            table_data,
            headers=["ID", "Type", "Details", "Added On", "Default"],
            tablefmt="pretty"
        ))
        
        click.echo("\nTo set a payment method as default: cabcab payment default <payment_id>")
        click.echo("To remove a payment method: cabcab payment remove <payment_id>")

    except (PaymentServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@payment_group.command(name="default")
@click.argument("payment_id", required=True)
@require_user_type([UserType.PASSENGER.value])
def set_default_payment(payment_id):
    """Set a payment method as your default."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Set the payment method as default
        updated_payment = PaymentService.set_default_payment_method(token, payment_id)
        
        click.echo(f"\n✅ {updated_payment['display_name']} has been set as your default payment method.")

    except (PaymentServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@payment_group.command(name="remove")
@click.argument("payment_id", required=True)
@click.option("--confirm", is_flag=True, help="Confirm removal without prompting")
@require_user_type([UserType.PASSENGER.value])
def remove_payment_method(payment_id, confirm):
    """Remove a payment method from your account."""
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get the payment method details first
        methods = PaymentService.get_payment_methods(token)
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
        success = PaymentService.remove_payment_method(token, payment_id)
        
        if success:
            click.echo("\n✅ Payment method removed successfully.")

    except (PaymentServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)