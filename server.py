#!/usr/bin/env python3
"""
Management script for the CabCab JSON server.
"""

import os
import sys
import subprocess
import signal
import time
import json
import click


@click.group()
def cli():
    """CabCab server management CLI."""
    pass


@cli.command()
@click.option('--port', default=3000, help='Port to run the server on')
def start(port):
    """Start the custom JSON server."""
    # Get the base directory (one level up from app directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pid_file = os.path.join(base_dir, 'server.pid')
    
    # Check if server is already running
    if os.path.exists(pid_file):
        with open(pid_file, 'r') as f:
            pid = f.read().strip()
        
        click.echo(f"Server already running with PID {pid}")
        click.echo(f"If the server is not running, delete the '{pid_file}' file and try again")
        return

    # Get the path to the server script
    server_script = os.path.join(base_dir, 'test_server.py')
    
    # Start the server in the background
    click.echo(f"Starting custom JSON server on port {port}...")
    
    try:
        # Start the server as a separate process
        process = subprocess.Popen([
            sys.executable,  # Use current Python interpreter
            server_script
        ], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE)
        
        # Save PID to file
        with open(pid_file, 'w') as f:
            f.write(str(process.pid))
            
        click.echo(f"Server running with PID {process.pid}")
        click.echo(f"Server accessible at: http://localhost:{port}")
        
        # Give the server a moment to start
        time.sleep(1)
        
        # Check if the server started successfully
        if process.poll() is not None:
            click.echo("Server failed to start!", err=True)
            stdout, stderr = process.communicate()
            click.echo(f"STDOUT: {stdout.decode('utf-8')}")
            click.echo(f"STDERR: {stderr.decode('utf-8')}")
            os.remove(pid_file)
            return
            
        click.echo("Server started successfully!")
        
    except Exception as e:
        click.echo(f"Error starting server: {str(e)}", err=True)
        if os.path.exists(pid_file):
            os.remove(pid_file)


@cli.command()
def stop():
    """Stop the JSON server."""
    # Get the base directory (one level up from app directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pid_file = os.path.join(base_dir, 'server.pid')
    
    if not os.path.exists(pid_file):
        click.echo("No running server found")
        return
    
    with open(pid_file, 'r') as f:
        pid = f.read().strip()
    
    try:
        pid = int(pid)
        click.echo(f"Stopping server with PID {pid}...")
        
        try:
            # Try to terminate gracefully first
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            
            # Check if process still exists
            try:
                os.kill(pid, 0)
                # If we get here, the process still exists, force kill it
                click.echo("Server did not terminate gracefully, force killing...")
                os.kill(pid, signal.SIGKILL)
            except OSError:
                # Process is gone
                pass
                
            click.echo("Server stopped")
        except OSError as e:
            click.echo(f"Error stopping server: {str(e)}")
            
        # Remove PID file
        os.remove(pid_file)
            
    except ValueError:
        click.echo(f"Invalid PID in the file: {pid}")
        os.remove(pid_file)


@cli.command()
def status():
    """Check if the JSON server is running."""
    # Get the base directory (one level up from app directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pid_file = os.path.join(base_dir, 'server.pid')
    
    if not os.path.exists(pid_file):
        click.echo("Server is not running")
        return
    
    with open(pid_file, 'r') as f:
        pid = f.read().strip()
    
    try:
        pid = int(pid)
        # Check if process exists
        try:
            os.kill(pid, 0)
            click.echo(f"Server is running with PID {pid}")
        except OSError:
            click.echo("Server PID file exists but process is not running")
            click.echo("You may want to remove the 'server.pid' file")
    except ValueError:
        click.echo(f"Invalid PID in the file: {pid}")


@cli.command()
def reset():
    """Reset the database to empty state."""
    # Get the base directory (one level up from app directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'data', 'db.json')
    
    if os.path.exists(db_path):
        try:
            # Create a backup of the current db
            backup_path = f"{db_path}.bak"
            with open(db_path, 'r') as src:
                with open(backup_path, 'w') as dst:
                    dst.write(src.read())
            
            # Reset the database to empty state
            with open(db_path, 'w') as f:
                f.write('{"users":[],"drivers":[],"vehicles":[],"locations":[],"rides":[],"payments":[]}')
                
            click.echo(f"Database reset. Backup created at {backup_path}")
        except Exception as e:
            click.echo(f"Error resetting database: {str(e)}")
    else:
        click.echo(f"Database file not found: {db_path}")


if __name__ == '__main__':
    cli()