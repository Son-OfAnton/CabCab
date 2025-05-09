"""Main CLI entry point for CabCab application."""

import click

# Import the CLI components - we need to avoid putting these in a separate module
# to prevent import errors with setuptools entry_points
from app.cli_module.commands.auth_commands import auth_group
from app.cli_module.commands.driver_commands import driver_group
from app.cli_module.commands.admin_commands import admin_group
from app.cli_module.commands.vehicle_commands import vehicle_group
from app.cli_module.commands.run_commands import run_command


@click.group()
def cli():
    """CabCab CLI application."""
    pass


# Register all command groups
cli.add_command(auth_group)
cli.add_command(driver_group)
cli.add_command(admin_group)
cli.add_command(vehicle_group)
cli.add_command(run_command)


def main():
    """Entry point for the application."""
    cli()


if __name__ == '__main__':
    main()