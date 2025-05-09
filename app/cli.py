"""Main CLI entry point for CabCab application."""

import click

from app.cli.commands import (
    auth_group,
    driver_group,
    admin_group,
    vehicle_group,
    run_command,
)


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