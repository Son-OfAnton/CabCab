"""Command Line Interface for CabCab application."""

import os
import click
import json
from app.main import process_command
from app.auth import AuthService, AuthError

# Config file to store auth token
CONFIG_DIR = os.path.expanduser("~/.cabcab")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def save_token(token: str) -> None:
    """Save auth token to config file."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"token": token}, f)


def get_token() -> str:
    """Get auth token from config file."""
    if not os.path.exists(CONFIG_FILE):
        return None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get("token")
    except json.JSONDecodeError:
        return None


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    token = get_token()
    
    if not token:
        return False
        
    try:
        AuthService.verify_token(token)
        return True
    except AuthError:
        return False


@click.group()
def cli():
    """CabCab CLI application."""
    pass


@cli.group()
def auth():
    """Authentication commands."""
    pass


@auth.command()
@click.option("--email", prompt=True, help="Your email address")
@click.option("--password", prompt=True, hide_input=True, help="Your password")
@click.option("--first-name", prompt=True, help="Your first name")
@click.option("--last-name", prompt=True, help="Your last name")
@click.option("--phone", prompt=True, help="Your phone number")
def signup(email, password, first_name, last_name, phone):
    """Register a new user."""
    try:
        result = AuthService.register(email, password, first_name, last_name, phone)
        save_token(result["token"])
        click.echo(f"User {first_name} {last_name} registered successfully!")
        click.echo(f"Email: {email}")
        click.echo("You are now logged in.")
    except AuthError as e:
        click.echo(f"Error during signup: {str(e)}", err=True)


@auth.command()
@click.option("--email", prompt=True, help="Your email address")
@click.option("--password", prompt=True, hide_input=True, help="Your password")
def signin(email, password):
    """Log in with credentials."""
    try:
        result = AuthService.login(email, password)
        save_token(result["token"])
        user = result["user"]
        click.echo(f"Welcome back, {user['first_name']} {user['last_name']}!")
        click.echo("You are now logged in.")
    except AuthError as e:
        click.echo(f"Error during signin: {str(e)}", err=True)


@auth.command()
def signout():
    """Log out from the application."""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        click.echo("You have been signed out.")
    else:
        click.echo("You were not signed in.")


@auth.command()
def whoami():
    """Show current user information."""
    token = get_token()
    
    if not token:
        click.echo("You are not signed in.", err=True)
        return
    
    try:
        user = AuthService.verify_token(token)
        click.echo(f"Signed in as: {user['first_name']} {user['last_name']}")
        click.echo(f"Email: {user['email']}")
        click.echo(f"Phone: {user['phone']}")
    except AuthError as e:
        click.echo(f"Session error: {str(e)}", err=True)
        click.echo("Please sign in again.")


@cli.command()
@click.argument('command', required=True)
@click.option('--option', '-o', help='Optional parameter.')
def run(command, option):
    """Execute a CabCab command."""
    # Check if authenticated (except for help/version commands)
    if command not in ['help', 'version'] and not is_authenticated():
        click.echo("You need to sign in first. Use 'cabcab auth signin' to log in.", err=True)
        return
    
    result = process_command(command, option)
    click.echo(result)


def main():
    """Entry point for the application."""
    cli()


if __name__ == '__main__':
    main()