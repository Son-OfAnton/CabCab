"""Run command for executing arbitrary CabCab commands."""

import click

from app.main import process_command
from app.cli_module.utils import is_authenticated


@click.command(name="run", help="Execute a CabCab command")
@click.argument('command', required=True, metavar="COMMAND")
@click.option('--option', '-o', help='Optional parameter for the command')
def run_command(command, option):
    """
    Execute a CabCab command.
    
    COMMAND: The command to execute.
    """
    # Check if authenticated (except for help/version commands)
    if command not in ['help', 'version'] and not is_authenticated():
        click.echo("You need to sign in first. Use 'cabcab auth signin' to log in.", err=True)
        return
    
    result = process_command(command, option)
    click.echo(result)