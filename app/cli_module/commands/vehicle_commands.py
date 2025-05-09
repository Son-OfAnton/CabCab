"""Vehicle management commands for the CabCab CLI."""

import click
from typing import Dict, Any

from app.services.vehicle_service import VehicleService, VehicleServiceError
from app.services.auth_service import AuthError, UserType
from app.cli_module.utils import get_token, require_user_type


@click.group(name="vehicle")
def vehicle_group():
    """Vehicle management commands."""
    pass


@vehicle_group.command()
@click.option("--make", prompt=True, help="Vehicle manufacturer")
@click.option("--model", prompt=True, help="Vehicle model")
@click.option("--year", prompt=True, type=int, help="Vehicle year")
@click.option("--color", prompt=True, help="Vehicle color")
@click.option("--license-plate", prompt=True, help="Vehicle license plate number")
@click.option("--type", "vehicle_type", prompt=True, 
              type=click.Choice(['ECONOMY', 'COMFORT', 'PREMIUM', 'SUV', 'XL'], case_sensitive=False),
              help="Vehicle type")
@click.option("--capacity", prompt=True, type=int, default=4,
              help="Maximum passenger capacity (default: 4)")
@require_user_type([UserType.DRIVER.value])
def register(make, model, year, color, license_plate, vehicle_type, capacity):
    """Register a new vehicle."""
    token = get_token()
    
    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return
    
    try:
        vehicle = VehicleService.register_vehicle(
            token, make, model, year, color, license_plate, vehicle_type, capacity
        )
        
        click.echo(f"Vehicle registered successfully!")
        click.echo(f"Make: {vehicle['make']}")
        click.echo(f"Model: {vehicle['model']}")
        click.echo(f"Year: {vehicle['year']}")
        click.echo(f"License Plate: {vehicle['license_plate']}")
        click.echo(f"Type: {vehicle['vehicle_type']}")
        click.echo(f"Capacity: {vehicle['capacity']} passengers")
        click.echo(f"Vehicle ID: {vehicle['id']}")
        
    except (VehicleServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@vehicle_group.command()
@require_user_type([UserType.DRIVER.value])
def list():
    """List all your vehicles."""
    token = get_token()
    
    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return
    
    try:
        vehicles = VehicleService.get_driver_vehicles(token)
        
        if not vehicles:
            click.echo("You have no registered vehicles.")
            return
        
        click.echo(f"You have {len(vehicles)} registered vehicle(s):")
        
        for i, vehicle in enumerate(vehicles, 1):
            click.echo(f"\nVehicle {i}:")
            click.echo(f"  ID: {vehicle['id']}")
            click.echo(f"  Make: {vehicle['make']}")
            click.echo(f"  Model: {vehicle['model']}")
            click.echo(f"  Year: {vehicle['year']}")
            click.echo(f"  Color: {vehicle['color']}")
            click.echo(f"  License Plate: {vehicle['license_plate']}")
            click.echo(f"  Type: {vehicle['vehicle_type']}")
            click.echo(f"  Capacity: {vehicle['capacity']} passengers")
            
    except (VehicleServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@vehicle_group.command()
@click.argument("vehicle_id")
@click.option("--make", help="Update vehicle manufacturer")
@click.option("--model", help="Update vehicle model")
@click.option("--year", type=int, help="Update vehicle year")
@click.option("--color", help="Update vehicle color")
@click.option("--license-plate", help="Update vehicle license plate")
@click.option("--type", "vehicle_type", 
              type=click.Choice(['ECONOMY', 'COMFORT', 'PREMIUM', 'SUV', 'XL'], case_sensitive=False),
              help="Update vehicle type")
@click.option("--capacity", type=int, help="Update maximum passenger capacity")
@click.option("--active/--inactive", default=None, help="Set vehicle active status")
@require_user_type([UserType.DRIVER.value])
def update(vehicle_id, make, model, year, color, license_plate, vehicle_type, capacity, active):
    """Update vehicle information."""
    token = get_token()
    
    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return
    
    # Collect update data
    update_data = {}
    if make:
        update_data['make'] = make
    if model:
        update_data['model'] = model
    if year:
        update_data['year'] = year
    if color:
        update_data['color'] = color
    if license_plate:
        update_data['license_plate'] = license_plate
    if vehicle_type:
        update_data['vehicle_type'] = vehicle_type
    if capacity:
        update_data['capacity'] = capacity
    if active is not None:
        update_data['is_active'] = active

    if not update_data:
        click.echo("No update information provided. Use the options to specify what to update.")
        click.echo("Example: cabcab vehicle update abc123 --color \"Blue\"")
        return
    
    try:
        updated_vehicle = VehicleService.update_vehicle(token, vehicle_id, update_data)
        
        click.echo("Vehicle updated successfully!")
        click.echo(f"Make: {updated_vehicle['make']}")
        click.echo(f"Model: {updated_vehicle['model']}")
        click.echo(f"Year: {updated_vehicle['year']}")
        click.echo(f"Color: {updated_vehicle['color']}")
        click.echo(f"License Plate: {updated_vehicle['license_plate']}")
        click.echo(f"Type: {updated_vehicle['vehicle_type']}")
        click.echo(f"Capacity: {updated_vehicle['capacity']} passengers")
        click.echo(f"Status: {'Active' if updated_vehicle['is_active'] else 'Inactive'}")
        
    except (VehicleServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)


@vehicle_group.command()
@click.argument("vehicle_id")
@click.option("--confirm", is_flag=True, help="Confirm deletion without prompting")
@require_user_type([UserType.DRIVER.value])
def delete(vehicle_id, confirm):
    """Delete a vehicle."""
    token = get_token()
    
    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return
    
    try:
        # First get the vehicle to show details before deleting
        vehicle = VehicleService.get_vehicle_by_id(vehicle_id)
        
        click.echo(f"Vehicle: {vehicle['make']} {vehicle['model']} ({vehicle['year']})")
        click.echo(f"License Plate: {vehicle['license_plate']}")
        
        # Confirm deletion
        if not confirm and not click.confirm("Are you sure you want to delete this vehicle?"):
            click.echo("Vehicle deletion cancelled.")
            return
        
        success = VehicleService.delete_vehicle(token, vehicle_id)
        
        if success:
            click.echo("Vehicle deleted successfully.")
        else:
            click.echo("Failed to delete vehicle.", err=True)
            
    except (VehicleServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)