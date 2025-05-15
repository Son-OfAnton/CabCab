"""Utility functions for the CLI interface."""

from functools import wraps
import os
import json
from typing import Optional, List

import click
from app.services.auth_service import AuthService, AuthError, AuthValidationError, validate_user_not_banned

# Config file to store auth token
CONFIG_DIR = os.path.expanduser("~/.cabcab")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def save_token(token: str) -> None:
    """Save auth token to config file."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"token": token}, f)


def get_token() -> Optional[str]:
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


# Enhanced decorator for requiring specific user types that also checks for bans
def require_user_type(required_types: List[str]):
    """
    Enhanced decorator to require specific user types and check for bans.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            token = get_token()
            if not token:
                click.echo("You are not signed in. Please sign in first.", err=True)
                return
            
            try:
                # First check that the user has required type
                AuthService.require_user_type(token, required_types)
                
                # Then check if user is banned (applies to passengers only)
                # Admin users are exempt from ban checks in validate_user_not_banned
                validate_user_not_banned(token)
                
                return f(*args, **kwargs)
                
            except AuthError as e:
                click.echo(f"Access denied: {str(e)}", err=True)
                return
            except AuthValidationError as e:
                click.echo(f"Account restricted: {str(e)}", err=True)
                return
        return wrapped
    return decorator