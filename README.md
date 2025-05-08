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
./cabcab

# For server management
./cabcab-server
```

## Server Setup

CabCab uses a custom JSON server for data storage and retrieval.

### Starting and Managing the Server

```bash
# Start the JSON server
./cabcab-server start

# Check server status
./cabcab-server status

# Stop the server
./cabcab-server stop

# Reset the database
./cabcab-server reset
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
./cabcab auth signup
```

You will be prompted for your email, password, first name, last name, and phone number.

### Signin

Log in to your existing account:

```bash
./cabcab auth signin
```

You will be prompted for your email and password.

### Check Current User

View your current user information:

```bash
./cabcab auth whoami
```

### Signout

Sign out from your account:

```bash
./cabcab auth signout
```

## Usage

After authentication, you can use the CLI application:

```bash
./cabcab run hello
./cabcab run hello --option value
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

1. Check if there's already a server running with `./cabcab-server status`
2. If the server.pid file exists but the server isn't running, delete the file
3. Check the server logs for error messages