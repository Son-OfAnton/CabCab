"""Admin-specific commands for the CabCab CLI."""

from datetime import datetime
import click
import requests
from tabulate import tabulate

from app.services.auth_service import AuthError, UserType
from app.services.ride_service import RideService, RideServiceError
from app.services.user_service import UserService, UserServiceError
from app.cli_module.utils import get_token, require_user_type
from app.cli_module.commands.admin_ban_commands import ban_group
from app.services.vehicle_service import VehicleService, VehicleServiceError


@click.group(name="admin", help="Admin specific commands for system management")
def admin_group():
    """Admin specific commands for system management and driver verification."""
    pass


# Add the ban commands as a subgroup
admin_group.add_command(ban_group)


@admin_group.command(name="verify_driver", help="Verify or unverify a driver account by email.")
@click.argument('email', metavar="EMAIL")
@click.option("--verify/--unverify", required=True,
              help="Set to --verify to verify the driver or --unverify to remove verification")
@require_user_type([UserType.ADMIN.value])
def verify_driver(email, verify):
    """
    Verify or unverify a driver's account.

    EMAIL: The email address of the driver to verify or unverify.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Find the user by email
        response = requests.get(
            f"http://localhost:3000/users/query?email={email}")

        if response.status_code == 404:
            click.echo(f"No user found with email {email}", err=True)
            return

        response.raise_for_status()
        users = response.json()

        if not users:
            click.echo(f"No user found with email {email}", err=True)
            return

        # Get the first user with the specified email
        user = users[0]

        # Check if user is a driver
        if user.get('user_type') != UserType.DRIVER.value:
            click.echo(f"User with email {email} is not a driver.", err=True)
            return

        # Update verification status
        user['is_verified'] = verify
        user['updated_at'] = datetime.now().isoformat()

        # Save the updated user
        response = requests.put(
            f"http://localhost:3000/users/{user['id']}", json=user)
        response.raise_for_status()

        verification_status = 'verified' if verify else 'unverified'
        click.echo(
            f"Driver {user['first_name']} {user['last_name']} ({email}) has been {verification_status}.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@admin_group.command(name="driver-info", help="View contact information of a driver by ID or email.")
@click.option('--id', 'driver_id', help='Driver ID')
@click.option('--email', help='Driver email')
@require_user_type([UserType.ADMIN.value])
def driver_info(driver_id, email):
    """
    View detailed contact information of a driver by ID or email.

    Requires admin privileges.
    """
    if not driver_id and not email:
        click.echo("Error: You must provide either --id or --email", err=True)
        return

    token = get_token()
    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Use the service to get driver information
        driver_data = UserService.get_driver_info(token, driver_id, email)

        # Extract the data
        user = driver_data['user']
        driver = driver_data['driver']
        vehicle = driver_data['vehicle']

        # Display the contact information
        click.echo(f"\n--- Driver Contact Information ---")
        click.echo(f"ID: {user['id']}")
        click.echo(f"Name: {user['first_name']} {user['last_name']}")
        click.echo(f"Email: {user['email']}")
        click.echo(f"Phone: {user['phone']}")

        # Add driver-specific information if available
        if driver.get('license_number') and driver['license_number'] != 'Not provided':
            click.echo(f"License Number: {driver['license_number']}")
        else:
            click.echo(f"License Number: Not provided")

        # Show verification status
        verification_status = "Verified" if driver.get(
            'is_verified') else "Not Verified"
        click.echo(f"Verification Status: {verification_status}")

        # Show account status
        account_status = "Active" if driver.get('is_active') else "Inactive"
        click.echo(f"Account Status: {account_status}")

        # Show rating information
        if isinstance(driver.get('rating'), (int, float)):
            click.echo(f"Rating: {driver['rating']}/5.0")
        else:
            click.echo(f"Rating: Not rated yet")

        # Show date joined
        if driver.get('created_at'):
            # Try to format the date nicely if it's in ISO format
            try:
                created_date = datetime.fromisoformat(
                    driver['created_at'].replace('Z', '+00:00'))
                click.echo(f"Joined: {created_date.strftime('%B %d, %Y')}")
            except (ValueError, AttributeError):
                click.echo(f"Joined: {driver['created_at']}")

        # Show vehicle information if available
        if vehicle:
            click.echo("\n--- Vehicle Information ---")
            vehicle_year = vehicle.get('year', 'N/A')
            vehicle_make = vehicle.get('make', 'N/A')
            vehicle_model = vehicle.get('model', 'N/A')
            click.echo(
                f"Vehicle: {vehicle_year} {vehicle_make} {vehicle_model}")
            click.echo(f"Color: {vehicle.get('color', 'N/A')}")
            click.echo(f"License Plate: {vehicle.get('license_plate', 'N/A')}")
            click.echo(f"Type: {vehicle.get('vehicle_type', 'N/A')}")
            click.echo(
                f"Capacity: {vehicle.get('capacity', 'N/A')} passengers")
        else:
            click.echo("\n--- Vehicle Information ---")
            click.echo("No vehicle information available")

    except UserServiceError as e:
        click.echo(f"Error: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)


@admin_group.command(name="passenger-info", help="View contact information of a passenger by ID or email.")
@click.option('--id', 'passenger_id', help='Passenger ID')
@click.option('--email', help='Passenger email')
@require_user_type([UserType.ADMIN.value])
def passenger_info(passenger_id, email):
    """
    View detailed contact information of a passenger by ID or email.

    Requires admin privileges.
    """
    if not passenger_id and not email:
        click.echo("Error: You must provide either --id or --email", err=True)
        return

    token = get_token()
    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Use the service to get passenger information
        passenger = UserService.get_passenger_info(token, passenger_id, email)

        # Display the contact information
        click.echo(f"\n--- Passenger Contact Information ---")
        click.echo(f"ID: {passenger['id']}")
        click.echo(f"Name: {passenger['first_name']} {passenger['last_name']}")
        click.echo(f"Email: {passenger['email']}")
        click.echo(f"Phone: {passenger['phone']}")

        # Show account status
        if passenger.get('is_banned', False):
            click.echo("Status: Banned")

            # Show ban details
            if passenger.get('permanent_ban', False):
                click.echo("Ban Type: Permanent")
            else:
                click.echo("Ban Type: Temporary")

            if passenger.get('banned_reason'):
                click.echo(f"Ban Reason: {passenger.get('banned_reason')}")

            if passenger.get('banned_at'):
                try:
                    banned_date = datetime.fromisoformat(
                        passenger.get('banned_at').replace('Z', '+00:00'))
                    click.echo(
                        f"Banned On: {banned_date.strftime('%B %d, %Y')}")
                except (ValueError, AttributeError):
                    click.echo(f"Banned On: {passenger.get('banned_at')}")

            if passenger.get('banned_by'):
                click.echo(f"Banned By: {passenger.get('banned_by')}")
        elif passenger.get('is_active', True):
            click.echo("Status: Active")
        else:
            click.echo("Status: Inactive")

        # Show date joined
        if passenger.get('created_at'):
            # Try to format the date nicely if it's in ISO format
            try:
                created_date = datetime.fromisoformat(
                    passenger.get('created_at').replace('Z', '+00:00'))
                click.echo(f"Joined: {created_date.strftime('%B %d, %Y')}")
            except (ValueError, AttributeError):
                click.echo(f"Joined: {passenger.get('created_at')}")

        # Display payment methods if available
        payment_methods = passenger.get('payment_methods', [])
        if payment_methods:
            click.echo("\n--- Payment Methods ---")
            for i, pm in enumerate(payment_methods, 1):
                method_type = pm.get('type', 'Unknown')
                details = pm.get('details', {})

                click.echo(f"{i}. {method_type}")

                # Format credit card details
                if method_type == 'CREDIT_CARD' and isinstance(details, dict):
                    if 'card_last4' in details:
                        click.echo(
                            f"   Card ending in: {details.get('card_last4')}")
                    if 'card_type' in details:
                        click.echo(f"   Card type: {details.get('card_type')}")
                    if 'expires' in details:
                        click.echo(f"   Expires: {details.get('expires')}")
                # Format other payment types as needed
        else:
            click.echo("\n--- Payment Methods ---")
            click.echo("No payment methods found")

        # Display ride statistics
        click.echo("\n--- Ride Statistics ---")
        total_rides = passenger.get('total_rides', 0)
        completed_rides = passenger.get('completed_rides', 0)
        cancelled_rides = passenger.get('cancelled_rides', 0)

        click.echo(f"Total Rides: {total_rides}")
        click.echo(f"Completed Rides: {completed_rides}")
        click.echo(f"Cancelled Rides: {cancelled_rides}")

        # Completion rate if they have rides
        if total_rides > 0:
            completion_rate = (completed_rides / total_rides) * 100
            click.echo(f"Completion Rate: {completion_rate:.1f}%")

        # Average rating given to drivers
        avg_rating = passenger.get('avg_rating_given')
        if avg_rating is not None:
            click.echo(f"Average Rating Given: {avg_rating:.1f}/5.0")
        else:
            click.echo("Average Rating Given: Not available")

        # Display status distribution
        statuses = passenger.get('ride_statuses', {})
        if statuses:
            click.echo("\n--- Ride Status Distribution ---")
            for status, count in sorted(statuses.items()):
                click.echo(f"{status}: {count}")

        # Display recent rides if available
        recent_rides = passenger.get('recent_rides', [])
        if recent_rides:
            click.echo("\n--- Recent Rides ---")
            for i, ride in enumerate(recent_rides, 1):
                ride_id = ride.get('id', 'Unknown')
                status = ride.get('status', 'Unknown')

                # Format date
                created_at = ride.get('created_at', '')
                try:
                    ride_date = datetime.fromisoformat(
                        created_at.replace('Z', '+00:00'))
                    date_display = ride_date.strftime('%Y-%m-%d %H:%M')
                except (ValueError, AttributeError):
                    date_display = created_at

                # Try to get pickup/dropoff locations
                pickup_loc = "Unknown"
                dropoff_loc = "Unknown"

                if ride.get('pickup_location_id'):
                    try:
                        loc_response = requests.get(
                            f"http://localhost:3000/locations/{ride.get('pickup_location_id')}")
                        if loc_response.status_code == 200:
                            location = loc_response.json()
                            pickup_loc = location.get('address', 'Unknown')
                    except Exception:
                        pass

                if ride.get('dropoff_location_id'):
                    try:
                        loc_response = requests.get(
                            f"http://localhost:3000/locations/{ride.get('dropoff_location_id')}")
                        if loc_response.status_code == 200:
                            location = loc_response.json()
                            dropoff_loc = location.get('address', 'Unknown')
                    except Exception:
                        pass

                click.echo(f"{i}. Ride ID: {ride_id}")
                click.echo(f"   Date: {date_display}")
                click.echo(f"   Status: {status}")
                click.echo(f"   Pickup: {pickup_loc}")
                click.echo(f"   Dropoff: {dropoff_loc}")

                # Show rating if available
                if ride.get('driver_rating') is not None:
                    click.echo(
                        f"   Rating Given: {ride.get('driver_rating')}/5.0")

                # Add some space between rides
                if i < len(recent_rides):
                    click.echo("")

    except UserServiceError as e:
        click.echo(f"Error: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)


@admin_group.command(name="list-drivers", help="List all drivers registered on the platform.")
@click.option('--active-only', is_flag=True, help='Show only active drivers')
@click.option('--verified-only', is_flag=True, help='Show only verified drivers')
@click.option('--available-only', is_flag=True, help='Show only available drivers')
@click.option('--format', 'output_format', type=click.Choice(['table', 'detailed'], case_sensitive=False),
              default='table', help='Output format (table or detailed)')
@require_user_type([UserType.ADMIN.value])
def list_drivers(active_only, verified_only, available_only, output_format):
    """
    List all drivers registered on the platform with optional filtering.

    Requires admin privileges.
    """
    token = get_token()
    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get the list of drivers using our service method
        drivers = UserService.list_all_drivers(
            token, active_only, verified_only)

        # If no drivers were found
        if not drivers:
            click.echo("No drivers found matching the specified criteria.")
            return

        # Filter for available drivers if requested
        if available_only:
            drivers = [d for d in drivers if d.get('is_available', False)]
            if not drivers:
                click.echo(
                    "No available drivers found matching the specified criteria.")
                return

        # Count total drivers
        total_drivers = len(drivers)

        # Output format: table (default) or detailed
        if output_format == 'table':
            # Prepare table data
            table_data = []
            headers = ["ID", "Name", "Email", "Phone", "Status",
                       "Verified", "Available", "Rating", "Rides", "Vehicle"]

            for driver in drivers:
                # Format the driver data for the table
                name = f"{driver.get('first_name', '')} {driver.get('last_name', '')}"
                status = "Active" if driver.get(
                    'is_active', True) else "Inactive"
                verified = "✓" if driver.get('is_verified', False) else "✗"
                available = "✓" if driver.get('is_available', False) else "✗"

                rating = driver.get('rating')
                if rating is None or rating == "":
                    rating_display = "N/A"
                else:
                    rating_display = f"{rating}/5.0"

                rides = f"{driver.get('completed_rides', 0)}/{driver.get('total_rides', 0)}"

                if driver.get('has_vehicle', False) and driver.get('vehicle'):
                    vehicle = driver.get('vehicle')
                else:
                    vehicle = "None"

                # Add row to table
                table_data.append([
                    driver.get('id', ''),
                    name,
                    driver.get('email', ''),
                    driver.get('phone', ''),
                    status,
                    verified,
                    available,
                    rating_display,
                    rides,
                    vehicle
                ])

            # Display the table
            click.echo(f"\nTotal drivers: {total_drivers}")
            filters_applied = []
            if active_only:
                filters_applied.append("active only")
            if verified_only:
                filters_applied.append("verified only")
            if available_only:
                filters_applied.append("available only")

            if filters_applied:
                click.echo(f"Filters applied: {', '.join(filters_applied)}")

            click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))

        else:  # detailed view
            # For each driver, display detailed information
            click.echo(f"\nTotal drivers: {total_drivers}")

            for i, driver in enumerate(drivers, 1):
                click.echo(f"\n--- Driver {i}/{total_drivers} ---")
                click.echo(f"ID: {driver.get('id', '')}")
                click.echo(
                    f"Name: {driver.get('first_name', '')} {driver.get('last_name', '')}")
                click.echo(f"Email: {driver.get('email', '')}")
                click.echo(f"Phone: {driver.get('phone', '')}")

                # License number if available
                license_number = driver.get('license_number')
                if license_number and license_number != "":
                    click.echo(f"License: {license_number}")

                # Status information
                status = "Active" if driver.get(
                    'is_active', True) else "Inactive"
                click.echo(f"Status: {status}")

                verified = "Verified" if driver.get(
                    'is_verified', False) else "Not Verified"
                click.echo(f"Verification: {verified}")

                available = "Available" if driver.get(
                    'is_available', False) else "Not Available"
                click.echo(f"Availability: {available}")

                # Rating information
                rating = driver.get('rating')
                if rating is None or rating == "":
                    click.echo("Rating: Not rated yet")
                else:
                    click.echo(f"Rating: {rating}/5.0")

                # Ride statistics
                completed = driver.get('completed_rides', 0)
                total = driver.get('total_rides', 0)
                click.echo(
                    f"Rides: {completed} completed out of {total} total")

                # Vehicle information
                if driver.get('has_vehicle', False) and driver.get('vehicle'):
                    click.echo(f"Vehicle: {driver.get('vehicle')}")
                    vehicle_type = driver.get('vehicle_type')
                    if vehicle_type:
                        click.echo(f"Vehicle Type: {vehicle_type}")
                else:
                    click.echo("Vehicle: None registered")

                # Registration date if available
                if driver.get('created_at'):
                    try:
                        created_date = datetime.fromisoformat(
                            driver.get('created_at').replace('Z', '+00:00'))
                        click.echo(
                            f"Joined: {created_date.strftime('%B %d, %Y')}")
                    except (ValueError, AttributeError):
                        click.echo(f"Joined: {driver.get('created_at')}")

    except UserServiceError as e:
        click.echo(f"Error: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)


@admin_group.command(name="list-passengers", help="List all passengers registered on the platform.")
@click.option('--active-only', is_flag=True, help='Show only active passengers')
@click.option('--include-banned', is_flag=True, help='Include banned passengers')
@click.option('--format', 'output_format', type=click.Choice(['table', 'detailed'], case_sensitive=False),
              default='table', help='Output format (table or detailed)')
@require_user_type([UserType.ADMIN.value])
def list_passengers(active_only, include_banned, output_format):
    """
    List all passengers registered on the platform with optional filtering.

    Requires admin privileges.
    """
    token = get_token()
    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get the list of passengers using our service method
        passengers = UserService.list_all_passengers(
            token, active_only, include_banned)

        # If no passengers were found
        if not passengers:
            click.echo("No passengers found matching the specified criteria.")
            return

        # Count total passengers
        total_passengers = len(passengers)

        # Output format: table (default) or detailed
        if output_format == 'table':
            # Prepare table data
            table_data = []
            headers = ["ID", "Name", "Email", "Phone", "Status", "Total Rides",
                       "Completed", "Cancelled", "Avg Rating", "Payment Methods"]

            for passenger in passengers:
                # Format the passenger data for the table
                name = f"{passenger.get('first_name', '')} {passenger.get('last_name', '')}"

                # Status includes both active and ban status
                if passenger.get('is_banned', False):
                    status = "Banned"
                elif passenger.get('is_active', True):
                    status = "Active"
                else:
                    status = "Inactive"

                total_rides = passenger.get('total_rides', 0)
                completed_rides = passenger.get('completed_rides', 0)
                cancelled_rides = passenger.get('cancelled_rides', 0)

                # Average rating given to drivers
                avg_rating = passenger.get('avg_rating_given')
                if avg_rating is not None:
                    rating_display = f"{avg_rating:.1f}/5.0"
                else:
                    rating_display = "N/A"

                # Payment methods count
                payment_methods = passenger.get('payment_methods_count', 0)

                # Add row to table
                table_data.append([
                    passenger.get('id', ''),
                    name,
                    passenger.get('email', ''),
                    passenger.get('phone', ''),
                    status,
                    total_rides,
                    completed_rides,
                    cancelled_rides,
                    rating_display,
                    payment_methods
                ])

            # Display the table
            click.echo(f"\nTotal passengers: {total_passengers}")

            filters_applied = []
            if active_only:
                filters_applied.append("active only")
            if include_banned:
                filters_applied.append("including banned")

            if filters_applied:
                click.echo(f"Filters applied: {', '.join(filters_applied)}")

            click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))

        else:  # detailed view
            # For each passenger, display detailed information
            click.echo(f"\nTotal passengers: {total_passengers}")

            for i, passenger in enumerate(passengers, 1):
                click.echo(f"\n--- Passenger {i}/{total_passengers} ---")
                click.echo(f"ID: {passenger.get('id', '')}")
                click.echo(
                    f"Name: {passenger.get('first_name', '')} {passenger.get('last_name', '')}")
                click.echo(f"Email: {passenger.get('email', '')}")
                click.echo(f"Phone: {passenger.get('phone', '')}")

                # Status information
                if passenger.get('is_banned', False):
                    click.echo("Status: Banned")

                    # Show ban details
                    if passenger.get('permanent_ban', False):
                        click.echo("Ban Type: Permanent")
                    else:
                        click.echo("Ban Type: Temporary")

                    if passenger.get('banned_reason'):
                        click.echo(
                            f"Ban Reason: {passenger.get('banned_reason')}")

                    if passenger.get('banned_at'):
                        try:
                            banned_date = datetime.fromisoformat(
                                passenger.get('banned_at').replace('Z', '+00:00'))
                            click.echo(
                                f"Banned On: {banned_date.strftime('%B %d, %Y')}")
                        except (ValueError, AttributeError):
                            click.echo(
                                f"Banned On: {passenger.get('banned_at')}")

                    if passenger.get('banned_by'):
                        click.echo(f"Banned By: {passenger.get('banned_by')}")

                elif passenger.get('is_active', True):
                    click.echo("Status: Active")
                else:
                    click.echo("Status: Inactive")

                # Ride statistics
                total_rides = passenger.get('total_rides', 0)
                completed_rides = passenger.get('completed_rides', 0)
                cancelled_rides = passenger.get('cancelled_rides', 0)

                click.echo(f"Total Rides: {total_rides}")
                click.echo(f"Completed Rides: {completed_rides}")
                click.echo(f"Cancelled Rides: {cancelled_rides}")

                # Completion rate if they have rides
                if total_rides > 0:
                    completion_rate = (completed_rides / total_rides) * 100
                    click.echo(f"Completion Rate: {completion_rate:.1f}%")

                # Average rating given to drivers
                avg_rating = passenger.get('avg_rating_given')
                if avg_rating is not None:
                    click.echo(f"Average Rating Given: {avg_rating:.1f}/5.0")
                else:
                    click.echo("Average Rating Given: Not available")

                # Payment methods count
                payment_methods = passenger.get('payment_methods_count', 0)
                click.echo(f"Payment Methods: {payment_methods}")

                # Registration date if available
                if passenger.get('created_at'):
                    try:
                        created_date = datetime.fromisoformat(
                            passenger.get('created_at').replace('Z', '+00:00'))
                        click.echo(
                            f"Joined: {created_date.strftime('%B %d, %Y')}")
                    except (ValueError, AttributeError):
                        click.echo(f"Joined: {passenger.get('created_at')}")

    except UserServiceError as e:
        click.echo(f"Error: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)


@admin_group.command(name="driver-rides", help="View all rides a driver has accepted")
@click.argument("email", metavar="EMAIL")
@click.option("--status", help="Filter by ride status (e.g., COMPLETED, CANCELLED)")
@click.option("--format", "output_format", type=click.Choice(['table', 'detailed'], case_sensitive=False),
              default='table', help='Output format (table or detailed)')
@require_user_type([UserType.ADMIN.value])
def driver_rides(email, status, output_format):
    """
    View all rides a driver has accepted or completed.

    EMAIL: The email address of the driver to check.

    Requires admin privileges.
    """
    token = get_token()
    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Get driver rides using the RideService
        rides = RideService.get_driver_rides(token, email, status)

        if not rides:
            status_msg = f" with status '{status}'" if status else ""
            click.echo(
                f"No rides found for driver with email {email}{status_msg}.")
            return

        # Get driver details
        response = requests.get(
            f"http://localhost:3000/users/query?email={email}")
        driver = response.json()[
            0] if response.status_code == 200 and response.json() else None

        # Display driver info header
        if driver:
            click.echo(
                f"\nRides for driver: {driver.get('first_name')} {driver.get('last_name')} ({email})")
        else:
            click.echo(f"\nRides for driver: {email}")

        # Status filter info display
        if status:
            click.echo(f"Filtered by status: {status}")

        click.echo(f"Total rides found: {len(rides)}")

        # Format the results based on output_format
        if output_format == 'table':
            # Prepare table data
            table_data = []
            headers = ["ID", "Date", "Status", "Passenger",
                       "Pickup", "Dropoff", "Fare", "Rating"]

            for ride in rides:
                # Format ride information for the table

                # Format the request time
                ride_date = "Unknown"
                if ride.get('request_time'):
                    try:
                        dt = datetime.fromisoformat(
                            ride.get('request_time').replace('Z', '+00:00'))
                        ride_date = dt.strftime('%Y-%m-%d %H:%M')
                    except (ValueError, TypeError):
                        ride_date = ride.get('request_time')

                # Format passenger info
                passenger_info = "Unknown"
                if ride.get('passenger'):
                    passenger_info = ride.get('passenger').get(
                        'name', "Unknown Passenger")

                # Format pickup and dropoff addresses
                pickup_address = "Unknown"
                if ride.get('pickup_location') and ride.get('pickup_location').get('address'):
                    pickup_location = ride.get('pickup_location')
                    pickup_address = f"{pickup_location.get('address')}, {pickup_location.get('city')}"

                dropoff_address = "Unknown"
                if ride.get('dropoff_location') and ride.get('dropoff_location').get('address'):
                    dropoff_location = ride.get('dropoff_location')
                    dropoff_address = f"{dropoff_location.get('address')}, {dropoff_location.get('city')}"

                # Format fare information
                if ride.get('status') == "COMPLETED" and ride.get('actual_fare') is not None:
                    fare = f"${float(ride.get('actual_fare')):.2f}"
                elif ride.get('estimated_fare') is not None:
                    fare = f"${float(ride.get('estimated_fare')):.2f} (est.)"
                else:
                    fare = "Unknown"

                # Format rating
                rating = f"{ride.get('rating')}/5" if ride.get(
                    'rating') is not None else "Not rated"

                # Add row to table
                table_data.append([
                    ride.get('id', ''),
                    ride_date,
                    ride.get('status', 'Unknown'),
                    passenger_info,
                    pickup_address,
                    dropoff_address,
                    fare,
                    rating
                ])

            # Display the table
            click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))

        else:  # detailed view
            # For each ride, display detailed information
            for i, ride in enumerate(rides, 1):
                click.echo(f"\n--- Ride {i}/{len(rides)} ---")
                click.echo(f"ID: {ride.get('id', 'Unknown')}")
                click.echo(f"Status: {ride.get('status', 'Unknown')}")

                # Format date/time information
                if ride.get('request_time'):
                    try:
                        dt = datetime.fromisoformat(
                            ride.get('request_time').replace('Z', '+00:00'))
                        click.echo(
                            f"Request Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    except (ValueError, TypeError):
                        click.echo(f"Request Time: {ride.get('request_time')}")

                # Show passenger information
                click.echo("\nPassenger Information:")
                if ride.get('passenger'):
                    passenger = ride.get('passenger')
                    click.echo(f"  Name: {passenger.get('name', 'Unknown')}")
                    click.echo(
                        f"  Email: {passenger.get('email', 'Not provided')}")
                    click.echo(
                        f"  Phone: {passenger.get('phone', 'Not provided')}")
                else:
                    click.echo("  Passenger details not available")

                # Show vehicle information if available
                if ride.get('vehicle'):
                    vehicle = ride.get('vehicle')
                    click.echo("\nVehicle Information:")
                    click.echo(
                        f"  Vehicle: {vehicle.get('year', '')} {vehicle.get('make', '')} {vehicle.get('model', '')}")
                    click.echo(
                        f"  Color: {vehicle.get('color', 'Not provided')}")
                    click.echo(
                        f"  License Plate: {vehicle.get('license_plate', 'Not provided')}")

                # Show pickup and dropoff locations
                click.echo("\nPickup Location:")
                if ride.get('pickup_location'):
                    pickup = ride.get('pickup_location')
                    click.echo(
                        f"  Address: {pickup.get('address', 'Not provided')}")
                    click.echo(f"  City: {pickup.get('city', 'Not provided')}, " +
                               f"{pickup.get('state', '')} {pickup.get('postal_code', '')}")
                    if pickup.get('latitude') and pickup.get('longitude'):
                        click.echo(
                            f"  Coordinates: {pickup.get('latitude')}, {pickup.get('longitude')}")
                else:
                    click.echo("  Location details not available")

                click.echo("\nDropoff Location:")
                if ride.get('dropoff_location'):
                    dropoff = ride.get('dropoff_location')
                    click.echo(
                        f"  Address: {dropoff.get('address', 'Not provided')}")
                    click.echo(f"  City: {dropoff.get('city', 'Not provided')}, " +
                               f"{dropoff.get('state', '')} {dropoff.get('postal_code', '')}")
                    if dropoff.get('latitude') and dropoff.get('longitude'):
                        click.echo(
                            f"  Coordinates: {dropoff.get('latitude')}, {dropoff.get('longitude')}")
                else:
                    click.echo("  Location details not available")

                # Distance and duration
                if ride.get('distance'):
                    click.echo(f"\nDistance: {ride.get('distance')} km")
                if ride.get('duration'):
                    click.echo(
                        f"Estimated Duration: {ride.get('duration')} minutes")

                # Show fare information
                click.echo("\nFare Details:")
                if ride.get('estimated_fare') is not None:
                    click.echo(
                        f"  Estimated Fare: ${float(ride.get('estimated_fare')):.2f}")

                if ride.get('actual_fare') is not None:
                    click.echo(
                        f"  Actual Fare: ${float(ride.get('actual_fare')):.2f}")

                if ride.get('payment'):
                    payment = ride.get('payment')
                    click.echo(
                        f"  Payment Method: {payment.get('payment_method', 'Unknown')}")
                    click.echo(
                        f"  Payment Status: {payment.get('status', 'Unknown')}")

                # If ride completed, show rating and feedback
                if ride.get('status') == "COMPLETED":
                    click.echo("\nFeedback from Passenger:")
                    if ride.get('rating') is not None:
                        click.echo(f"  Rating: {ride.get('rating')}/5")
                    else:
                        click.echo("  Rating: Not provided")

                    if ride.get('feedback'):
                        click.echo(f"  Feedback: \"{ride.get('feedback')}\"")

                # Show earnings information (for completed rides)
                if ride.get('status') == "COMPLETED" and ride.get('actual_fare') is not None:
                    # In a real app, we would calculate the driver's earnings based on the fare
                    # This is a simplified example assuming the driver gets 80% of the fare
                    driver_earnings = float(ride.get('actual_fare')) * 0.8
                    click.echo(f"\nDriver Earnings: ${driver_earnings:.2f}")

                # Show timestamps for ride lifecycle
                click.echo("\nTimestamps:")
                if ride.get('start_time'):
                    try:
                        dt = datetime.fromisoformat(
                            ride.get('start_time').replace('Z', '+00:00'))
                        click.echo(
                            f"  Started: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    except (ValueError, TypeError):
                        click.echo(f"  Started: {ride.get('start_time')}")

                if ride.get('end_time'):
                    try:
                        dt = datetime.fromisoformat(
                            ride.get('end_time').replace('Z', '+00:00'))
                        click.echo(
                            f"  Ended: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    except (ValueError, TypeError):
                        click.echo(f"  Ended: {ride.get('end_time')}")

                # Add divider between rides
                if i < len(rides):
                    click.echo("\n" + "-" * 50)

    except (RideServiceError, UserServiceError, AuthError) as e:
        click.echo(f"Error: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)


# New command to add to admin_commands.py

@admin_group.command(name="search-vehicle", help="Search for a vehicle by license plate")
@click.argument("license_plate", metavar="LICENSE_PLATE")
@click.option("--format", "output_format", type=click.Choice(['table', 'detailed'], case_sensitive=False),
              default='table', help='Output format (table or detailed)')
@require_user_type([UserType.ADMIN.value])
def search_vehicle(license_plate, output_format):
    """
    Search for a vehicle by license plate.

    LICENSE_PLATE: The license plate to search for

    Requires admin privileges.
    """
    token = get_token()

    if not token:
        click.echo("You are not signed in. Please sign in first.", err=True)
        return

    try:
        # Search for the vehicle
        result = VehicleService.find_vehicle_by_license_plate(
            token, license_plate)

        vehicles = result.get('vehicles', [])
        count = result.get('count', 0)

        if count == 0:
            click.echo(
                f"No vehicles found with license plate similar to '{license_plate}'.")
            return

        # Display the number of matches
        if count == 1:
            click.echo(
                f"Found 1 vehicle with license plate similar to '{license_plate}':")
        else:
            click.echo(
                f"Found {count} vehicles with license plate similar to '{license_plate}':")

        # Display the results based on the selected format
        if output_format == 'table':
            # Prepare data for table display
            table_data = []
            headers = ["ID", "License Plate", "Make",
                       "Model", "Year", "Type", "Driver", "Status"]

            for vehicle in vehicles:
                # Vehicle details
                license_plate = vehicle.get('license_plate', 'Unknown')
                make = vehicle.get('make', 'Unknown')
                model = vehicle.get('model', 'Unknown')
                year = vehicle.get('year', 'Unknown')
                vehicle_type = vehicle.get('vehicle_type', 'Unknown')

                # Driver details
                driver_info = "Unknown"
                if 'driver' in vehicle and vehicle['driver']:
                    driver = vehicle['driver']
                    driver_name = driver.get('name', 'Unknown')
                    is_verified = "✓" if driver.get(
                        'is_verified', False) else "✗"
                    driver_info = f"{driver_name} ({is_verified})"

                # Vehicle status
                status = "Active" if vehicle.get(
                    'is_active', False) else "Inactive"

                # Add row to table
                table_data.append([
                    vehicle.get('id', 'Unknown'),
                    license_plate,
                    make,
                    model,
                    year,
                    vehicle_type,
                    driver_info,
                    status
                ])

            # Display the table
            click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))

        else:  # detailed format
            for i, vehicle in enumerate(vehicles, 1):
                click.echo(f"\n--- Vehicle {i}/{count} ---")

                # Vehicle basic info
                click.echo(f"ID: {vehicle.get('id', 'Unknown')}")
                click.echo(
                    f"License Plate: {vehicle.get('license_plate', 'Unknown')}")
                click.echo(f"Make: {vehicle.get('make', 'Unknown')}")
                click.echo(f"Model: {vehicle.get('model', 'Unknown')}")
                click.echo(f"Year: {vehicle.get('year', 'Unknown')}")
                click.echo(f"Color: {vehicle.get('color', 'Unknown')}")
                click.echo(f"Type: {vehicle.get('vehicle_type', 'Unknown')}")
                click.echo(
                    f"Capacity: {vehicle.get('capacity', 'Unknown')} passengers")
                click.echo(
                    f"Status: {'Active' if vehicle.get('is_active', False) else 'Inactive'}")

                # Registration date
                if 'created_at' in vehicle:
                    try:
                        created_date = datetime.fromisoformat(
                            vehicle['created_at'].replace('Z', '+00:00'))
                        click.echo(
                            f"Registered on: {created_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    except (ValueError, TypeError):
                        click.echo(
                            f"Registered on: {vehicle.get('created_at', 'Unknown')}")

                # Driver information
                click.echo("\nDriver Information:")
                if 'driver' in vehicle and vehicle['driver']:
                    driver = vehicle['driver']
                    click.echo(f"  Name: {driver.get('name', 'Unknown')}")
                    click.echo(f"  Email: {driver.get('email', 'Unknown')}")
                    click.echo(f"  Phone: {driver.get('phone', 'Unknown')}")
                    click.echo(
                        f"  Verification: {'Verified' if driver.get('is_verified', False) else 'Not Verified'}")
                    click.echo(
                        f"  Status: {'Active' if driver.get('is_active', False) else 'Inactive'}")
                else:
                    click.echo("  No driver information available")

                # Add a divider between vehicles if there are multiple
                if i < count:
                    click.echo("\n" + "-" * 50)

        # Show helpful commands that can be used with these results
        if count > 0:
            click.echo("\nHelpful commands:")
            for vehicle in vehicles:
                if 'driver' in vehicle and vehicle['driver']:
                    driver = vehicle['driver']
                    click.echo(
                        f"  cabcab admin driver-info --email {driver.get('email', '')}")

            click.echo(
                "  cabcab admin verify-driver --email <driver_email> --verify/--unverify")

    except VehicleServiceError as e:
        click.echo(f"Error: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
