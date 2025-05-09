"""Utility functions for the CLI interface."""

import os
import json
from typing import Optional, List

import click
from app.auth.auth_service import AuthService, AuthError

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


def require_user_type(required_types: List[str]):
    """Decorator to require specific user types."""
    def decorator(f):
        def wrapped(*args, **kwargs):
            token = get_token()
            if not token:
                click.echo("You are not signed in. Please sign in first.", err=True)
                return
            
            try:
                AuthService.require_user_type(token, required_types)
                return f(*args, **kwargs)
            except AuthError as e:
                click.echo(f"Access denied: {str(e)}", err=True)
                return
        return wrapped
    return decorator