# CabCab

A Python-based CLI application for ride-hailing services.

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/cabcab.git
cd cabcab
```

Install the package in development mode:

```bash
pip install -e .
```

## Server Setup

CabCab uses json-server-py as a mock backend server. To start the server:

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

## Authentication

### Signup

Register a new user account:

```bash
cabcab auth signup
```

You will be prompted for your email, password, first name, last name, and phone number.

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

## Usage

After authentication, you can use the CLI application:

```bash
cabcab run hello
cabcab run hello --option value
```

## Development

### Setup Development Environment

```bash
pip install -r requirements.txt
```

### Running Tests

```bash
pytest
```