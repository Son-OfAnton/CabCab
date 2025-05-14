import unittest
import json
import uuid
import responses
import jwt
from datetime import datetime, timedelta

from app.cli_module.commands.admin_commands import verify_driver
from app.services.auth_service import AuthService, UserType, JWT_SECRET, JWT_ALGORITHM
from click.testing import CliRunner


class TestDriverVerification(unittest.TestCase):
    """Test suite for the admin driver verification functionality."""

    def setUp(self):
        """Set up test case with mock admin, driver users, and tokens."""
        # Create a mock admin user
        self.admin_id = str(uuid.uuid4())
        self.admin = {
            "id": self.admin_id,
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "User",
            "phone": "555-123-4567",
            "user_type": UserType.ADMIN.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Generate a valid JWT token for the admin
        payload = {
            "user_id": self.admin_id,
            "user_type": UserType.ADMIN.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        self.admin_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Create a mock driver user
        self.driver_id = str(uuid.uuid4())
        self.driver_email = "driver@example.com"
        self.driver = {
            "id": self.driver_id,
            "email": self.driver_email,
            "first_name": "Test",
            "last_name": "Driver",
            "phone": "555-987-6543",
            "user_type": UserType.DRIVER.value,
            "license_number": "DL12345678",
            "is_verified": False,  # Driver starts as unverified
            "is_available": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Create a mock passenger user (for testing user type validation)
        self.passenger_id = str(uuid.uuid4())
        self.passenger_email = "passenger@example.com"
        self.passenger = {
            "id": self.passenger_id,
            "email": self.passenger_email,
            "first_name": "Test",
            "last_name": "Passenger",
            "user_type": UserType.PASSENGER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Create a regular user token (for testing permission validation)
        payload = {
            "user_id": self.driver_id,
            "user_type": UserType.DRIVER.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        self.driver_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Set up CLI runner for testing the command
        self.runner = CliRunner()
        
        # Start response mocking
        responses.start()

    def tearDown(self):
        """Clean up mocks after each test."""
        responses.stop()
        responses.reset()

    def _mock_token_file(self, token):
        """Helper method to mock token file for CLI commands."""
        config_dir = "/tmp/.cabcab"
        config_file = f"{config_dir}/config.json"
        
        # Create the config directory
        import os
        os.makedirs(config_dir, exist_ok=True)
        
        # Write the token to the config file
        with open(config_file, 'w') as f:
            json.dump({"token": token}, f)
            
        return config_file

    def _clean_token_file(self):
        """Helper method to clean up mock token file."""
        config_file = "/tmp/.cabcab/config.json"
        import os
        if os.path.exists(config_file):
            os.remove(config_file)

    @responses.activate
    def test_verify_driver_success(self):
        """Test successfully verifying a driver as admin."""
        # Set up token file for authentication
        self._mock_token_file(self.admin_token)
        
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the query for driver by email
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.driver_email}",
            json=[self.driver],
            status=200
        )
        
        # Mock the driver update endpoint
        expected_driver = self.driver.copy()
        expected_driver["is_verified"] = True
        expected_driver["updated_at"] = responses.matchers.ANY  # We don't care about the exact timestamp
        
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.driver_id}",
            json=expected_driver,
            status=200
        )
        
        # Run the verify command
        result = self.runner.invoke(verify_driver, [self.driver_email, "--verify"])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command ran successfully
        self.assertEqual(0, result.exit_code, f"Command failed with: {result.output}")
        
        # Check output contains verification confirmation
        self.assertIn("has been verified", result.output)
        self.assertIn(self.driver["first_name"], result.output)
        self.assertIn(self.driver["last_name"], result.output)

    @responses.activate
    def test_unverify_driver_success(self):
        """Test successfully unverifying a driver as admin."""
        # First make the driver verified
        verified_driver = self.driver.copy()
        verified_driver["is_verified"] = True
        
        # Set up token file for authentication
        self._mock_token_file(self.admin_token)
        
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the query for driver by email
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.driver_email}",
            json=[verified_driver],
            status=200
        )
        
        # Mock the driver update endpoint
        expected_driver = verified_driver.copy()
        expected_driver["is_verified"] = False
        expected_driver["updated_at"] = responses.matchers.ANY  # We don't care about the exact timestamp
        
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.driver_id}",
            json=expected_driver,
            status=200
        )
        
        # Run the unverify command
        result = self.runner.invoke(verify_driver, [self.driver_email, "--unverify"])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command ran successfully
        self.assertEqual(0, result.exit_code, f"Command failed with: {result.output}")
        
        # Check output contains unverification confirmation
        self.assertIn("has been unverified", result.output)
        self.assertIn(self.driver["first_name"], result.output)
        self.assertIn(self.driver["last_name"], result.output)

    @responses.activate
    def test_verify_driver_not_found(self):
        """Test error handling when driver email doesn't exist."""
        # Set up token file for authentication
        self._mock_token_file(self.admin_token)
        
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the query for driver by email with empty result
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email=nonexistent@example.com",
            json=[],
            status=200
        )
        
        # Run the verify command
        result = self.runner.invoke(verify_driver, ["nonexistent@example.com", "--verify"])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command failed with appropriate message
        self.assertNotEqual(0, result.exit_code)
        self.assertIn("No user found", result.output)

    @responses.activate
    def test_verify_non_driver_user(self):
        """Test error handling when trying to verify a non-driver user."""
        # Set up token file for authentication
        self._mock_token_file(self.admin_token)
        
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the query for passenger by email
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.passenger_email}",
            json=[self.passenger],
            status=200
        )
        
        # Run the verify command
        result = self.runner.invoke(verify_driver, [self.passenger_email, "--verify"])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command failed with appropriate message
        self.assertNotEqual(0, result.exit_code)
        self.assertIn("is not a driver", result.output)

    @responses.activate
    def test_verify_driver_without_admin_privileges(self):
        """Test error handling when non-admin tries to verify a driver."""
        # Set up token file for authentication with driver token (non-admin)
        self._mock_token_file(self.driver_token)
        
        # Mock the driver user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Run the verify command
        result = self.runner.invoke(verify_driver, [self.driver_email, "--verify"])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command failed with appropriate message
        self.assertNotEqual(0, result.exit_code)
        self.assertIn("Access denied", result.output)

    @responses.activate
    def test_verify_driver_with_expired_token(self):
        """Test error handling when admin token is expired."""
        # Create an expired token
        payload = {
            "user_id": self.admin_id,
            "user_type": UserType.ADMIN.value,
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Set up token file for authentication with expired token
        self._mock_token_file(expired_token)
        
        # Run the verify command
        result = self.runner.invoke(verify_driver, [self.driver_email, "--verify"])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command failed with appropriate message
        self.assertNotEqual(0, result.exit_code)

    @responses.activate
    def test_verify_driver_server_error(self):
        """Test error handling when server encounters an error."""
        # Set up token file for authentication
        self._mock_token_file(self.admin_token)
        
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the query for driver by email
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.driver_email}",
            json=[self.driver],
            status=200
        )
        
        # Mock the driver update endpoint with server error
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.driver_id}",
            status=500,
            json={"error": "Internal server error"}
        )
        
        # Run the verify command
        result = self.runner.invoke(verify_driver, [self.driver_email, "--verify"])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command failed with appropriate message
        self.assertNotEqual(0, result.exit_code)
        self.assertIn("Error", result.output)

    @responses.activate
    def test_verify_driver_missing_arguments(self):
        """Test error handling when command is missing required arguments."""
        # Set up token file for authentication
        self._mock_token_file(self.admin_token)
        
        # Run the verify command without required arguments
        result = self.runner.invoke(verify_driver, [self.driver_email])  # Missing --verify or --unverify
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command failed with usage info
        self.assertNotEqual(0, result.exit_code)
        self.assertIn("Error", result.output.lower())

    @responses.activate
    def test_verify_already_verified_driver(self):
        """Test verifying a driver that is already verified."""
        # Create an already verified driver
        verified_driver = self.driver.copy()
        verified_driver["is_verified"] = True
        
        # Set up token file for authentication
        self._mock_token_file(self.admin_token)
        
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the query for driver by email
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.driver_email}",
            json=[verified_driver],
            status=200
        )
        
        # Mock the driver update endpoint (even though nothing changes)
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.driver_id}",
            json=verified_driver,
            status=200
        )
        
        # Run the verify command
        result = self.runner.invoke(verify_driver, [self.driver_email, "--verify"])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command ran successfully (it should still work, even if already verified)
        self.assertEqual(0, result.exit_code, f"Command failed with: {result.output}")
        self.assertIn("has been verified", result.output)


if __name__ == '__main__':
    unittest.main()