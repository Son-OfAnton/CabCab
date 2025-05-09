"""Command modules for the CabCab CLI."""

from app.cli_module.commands.auth_commands import auth_group
from app.cli_module.commands.driver_commands import driver_group
from app.cli_module.commands.admin_commands import admin_group
from app.cli_module.commands.vehicle_commands import vehicle_group
from app.cli_module.commands.run_commands import run_command

__all__ = [
    'auth_group',
    'driver_group',
    'admin_group',
    'vehicle_group',
    'run_command',
]