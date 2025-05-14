"""Main CLI entry point for CabCab application."""

import click

# Set context settings to properly display help for all commands
CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 120,
    "show_default": True
}

# Import the CLI components directly from each module
from app.cli_module.commands.auth_commands import auth_group
from app.cli_module.commands.driver_commands import driver_group
from app.cli_module.commands.admin_commands import admin_group
from app.cli_module.commands.vehicle_commands import vehicle_group
from app.cli_module.commands.ride_commands import ride_group
from app.cli_module.commands.payment_commands import payment_group  # Add payment commands
from app.cli_module.commands.run_commands import run_command


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """CabCab CLI application for ride-hailing services."""
    pass


# Register all command groups
cli.add_command(auth_group)
cli.add_command(driver_group)
cli.add_command(admin_group)
cli.add_command(vehicle_group)
cli.add_command(ride_group)
cli.add_command(payment_group)  # Register the payment command group
cli.add_command(run_command)


def main():
    """Entry point for the application."""
    cli()


if __name__ == '__main__':
    main()