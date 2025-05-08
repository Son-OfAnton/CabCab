# CabCab

A Python-based CLI application for ride-hailing services.

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/cabcab.git
cd cabcab
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

You can run the application using the provided scripts:

```bash
# For main CLI commands
cabcab

# For server management
cabcab-server
```

## Server Setup

CabCab uses a custom JSON server for data storage and retrieval.

### Starting and Managing the Server

```bash
# Start the JSON server
cabcab-server start

# Check server status
cabcab-server status

# Stop the server
cabcab-server stop

# Reset the database
cabcab-server reset
```

### Direct server execution

You can also run the server directly:

```bash
# Start the server
python test_server.py
```

## Authentication

### Signup

Register a new user account:

```bash
# Register as a passenger
cabcab auth register passenger

# Register as a driver
cabcab auth register driver

# Register as an admin (requires authorization code)
cabcab auth register admin
```

You will be prompted for your details such as email, password, name, phone number, and additional fields depending on the user type.

### Signin

Log in to your existing account:

```bash
cabcab auth signin
```

You will be prompted for your email and password.

### Check Current User

View your current user information:

```bash
cabcab auth whoami
```

### Signout

Sign out from your account:

```bash
cabcab auth signout
```

### Update Profile

Update your profile information:

```bash
cabcab auth profile update --first-name "New Name" --last-name "New Last Name" --phone "1234567890"
```

### Change Password

Change your password:

```bash
cabcab auth profile change-password
```

You will be prompted for your current and new passwords.

## Driver Commands

### Set Availability

Set your availability to accept ride requests:

```bash
cabcab driver availability --status available
```

## Admin Commands

### Verify Driver

Verify or unverify a driver:

```bash
cabcab admin verify-driver <user_id> --verify
cabcab admin verify-driver <user_id> --unverify
```

## Usage

After authentication, you can use the CLI application:

```bash
cabcab run <command> --option value
```

## API Endpoints

The following endpoints are available in the custom JSON server:

- `GET /`: Get the entire database
- `GET /<collection>`: Get all items in a collection
- `POST /<collection>`: Add a new item to a collection
- `GET /<collection>/<id>`: Get an item by ID
- `PUT /<collection>/<id>`: Update an item
- `DELETE /<collection>/<id>`: Delete an item
- `GET /<collection>/query?param=value`: Query items by parameters

Collections available:

- users
- drivers
- vehicles
- locations
- rides
- payments

## Development

### Running Tests

```bash
pytest
```

## Troubleshooting

If you encounter issues with the server:

1. Check if there's already a server running with `cabcab-server status`
2. If the server.pid file exists but the server isn't running, delete the file
3. Check the server logs for error messages

## Project Structure

Below is the project structure:

```
CabCab/
├── app/
│   ├── __init__.py
│   ├── cli.py
│   ├── main.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   └── user_type.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── driver.py
│   │   └── ride.py
│   └── utils/
│       ├── __init__.py
│       ├── helpers.py
│       └── validators.py
├── tests/
│   ├── test_auth.py
│   ├── test_cli.py
│   └── test_server.py
├── cabcab
├── cabcab-server
├── requirements.txt
├── README.md
└── test_server.py
```
