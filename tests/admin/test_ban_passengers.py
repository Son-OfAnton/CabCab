import unittest
import json
import uuid
import responses
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.user_service import UserService, UserServiceError
from app.services.auth_service import AuthService, UserType, JWT_SECRET, JWT_ALGORITHM
from app.services.auth_service import validate_user_not_banned, AuthValidationError
from app.cli_module.commands.admin_ban_commands import ban_passenger, unban_passenger, list_banned_users, check_ban_status
from click.testing import CliRunner


class TestBanPassenger(unittest.TestCase):
    """Test suite for the admin passenger banning functionality."""

    def setUp(self):
        """Set up test cases with mock admin, passengers, and tokens."""
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
        
        # Create a mock passenger user
        self.passenger_id = str(uuid.uuid4())
        self.passenger_email = "passenger@example.com"
        self.passenger = {
            "id": self.passenger_id,
            "email": self.passenger_email,
            "first_name": "Test",
            "last_name": "Passenger",
            "phone": "555-987-6543",
            "user_type": UserType.PASSENGER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_banned": False,
            "payment_methods": []
        }
        
        # Generate a valid JWT token for the passenger
        payload = {
            "user_id": self.passenger_id,
            "user_type": UserType.PASSENGER.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        self.passenger_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Create a mock banned passenger
        self.banned_passenger_id = str(uuid.uuid4())
        self.banned_passenger_email = "banned@example.com"
        self.banned_passenger = {
            "id": self.banned_passenger_id,
            "email": self.banned_passenger_email,
            "first_name": "Banned",
            "last_name": "User",
            "phone": "555-111-2222",
            "user_type": UserType.PASSENGER.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_banned": True,
            "ban_reason": "Violation of terms of service",
            "is_permanent_ban": False,
            "banned_by": self.admin_id,
            "banned_at": datetime.now().isoformat(),
            "payment_methods": []
        }
        
        # Create a mock driver user (for testing user type validation)
        self.driver_id = str(uuid.uuid4())
        self.driver_email = "driver@example.com"
        self.driver = {
            "id": self.driver_id,
            "email": self.driver_email,
            "first_name": "Test",
            "last_name": "Driver",
            "user_type": UserType.DRIVER.value,
            "license_number": "DL12345678",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Generate a valid JWT token for the driver
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
        """ Helper method to mock token file for CLI commands. """
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
    def test_ban_passenger_success(self):
        """Test successfully banning a passenger as admin."""
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the passenger query endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.passenger_email}",
            json=[self.passenger],
            status=200
        )
        
        # Expected banned passenger data
        expected_banned_passenger = self.passenger.copy()
        expected_banned_passenger.update({
            "is_banned": True,
            "ban_reason": "Test ban reason",
            "is_permanent_ban": False,
            "banned_by": self.admin_id,
            "banned_at": responses.matchers.ANY,
            "updated_at": responses.matchers.ANY
        })
        
        # Mock the passenger update endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=expected_banned_passenger,
            status=200
        )
        
        # Mock the bans collection endpoint
        responses.add(
            responses.POST,
            f"http://localhost:3000/bans",
            json={
                "id": responses.matchers.ANY,
                "user_id": self.passenger_id,
                "user_email": self.passenger_email,
                "banned_by": self.admin_id,
                "admin_email": self.admin["email"],
                "reason": "Test ban reason",
                "is_permanent": False,
                "created_at": responses.matchers.ANY,
                "active": True
            },
            status=201
        )
        
        # Execute the ban
        result = UserService.ban_passenger(
            self.admin_token,
            self.passenger_email,
            reason="Test ban reason",
            permanent=False
        )
        
        # Verify the result
        self.assertTrue(result["is_banned"])
        self.assertEqual(result["ban_reason"], "Test ban reason")
        self.assertFalse(result["is_permanent_ban"])
        self.assertEqual(result["banned_by"], self.admin_id)
        self.assertEqual(result["email"], self.passenger_email)

    @responses.activate
    def test_ban_passenger_permanent(self):
        """Test permanently banning a passenger as admin."""
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the passenger query endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.passenger_email}",
            json=[self.passenger],
            status=200
        )
        
        # Expected banned passenger data
        expected_banned_passenger = self.passenger.copy()
        expected_banned_passenger.update({
            "is_banned": True,
            "ban_reason": "Serious violation",
            "is_permanent_ban": True,
            "banned_by": self.admin_id,
            "banned_at": responses.matchers.ANY,
            "updated_at": responses.matchers.ANY
        })
        
        # Mock the passenger update endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=expected_banned_passenger,
            status=200
        )
        
        # Mock the bans collection endpoint
        responses.add(
            responses.POST,
            f"http://localhost:3000/bans",
            json={
                "id": responses.matchers.ANY,
                "user_id": self.passenger_id,
                "user_email": self.passenger_email,
                "banned_by": self.admin_id,
                "admin_email": self.admin["email"],
                "reason": "Serious violation",
                "is_permanent": True,
                "created_at": responses.matchers.ANY,
                "active": True
            },
            status=201
        )
        
        # Execute the ban
        result = UserService.ban_passenger(
            self.admin_token,
            self.passenger_email,
            reason="Serious violation",
            permanent=True
        )
        
        # Verify the result
        self.assertTrue(result["is_banned"])
        self.assertEqual(result["ban_reason"], "Serious violation")
        self.assertTrue(result["is_permanent_ban"])
        self.assertEqual(result["banned_by"], self.admin_id)
        self.assertEqual(result["email"], self.passenger_email)

    @responses.activate
    def test_ban_already_banned_passenger(self):
        """Test error when trying to ban an already banned passenger."""
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the passenger query endpoint with already banned passenger
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.banned_passenger_email}",
            json=[self.banned_passenger],
            status=200
        )
        
        # Execute the ban and expect an error
        with self.assertRaises(UserServiceError) as context:
            UserService.ban_passenger(
                self.admin_token,
                self.banned_passenger_email,
                reason="New ban reason",
                permanent=False
            )
        
        self.assertIn("already banned", str(context.exception).lower())

    @responses.activate
    def test_ban_non_passenger_user(self):
        """Test error when trying to ban a non-passenger user."""
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the driver query endpoint 
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.driver_email}",
            json=[self.driver],
            status=200
        )
        
        # Execute the ban and expect an error
        with self.assertRaises(UserServiceError) as context:
            UserService.ban_passenger(
                self.admin_token,
                self.driver_email,
                reason="Invalid ban attempt",
                permanent=False
            )
        
        self.assertIn("not a passenger", str(context.exception).lower())

    @responses.activate
    def test_ban_passenger_not_found(self):
        """Test error when trying to ban a passenger that doesn't exist."""
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the passenger query endpoint with empty result
        non_existent_email = "nonexistent@example.com"
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={non_existent_email}",
            json=[],
            status=200
        )
        
        # Execute the ban and expect an error
        with self.assertRaises(UserServiceError) as context:
            UserService.ban_passenger(
                self.admin_token,
                non_existent_email,
                reason="Ban attempt on non-existent user",
                permanent=False
            )
        
        self.assertIn("not found", str(context.exception).lower())

    @responses.activate
    def test_ban_passenger_non_admin(self):
        """Test error when a non-admin user tries to ban a passenger."""
        # Mock the driver user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.driver_id}",
            json=self.driver,
            status=200
        )
        
        # Execute the ban and expect an error
        with self.assertRaises(Exception) as context:
            UserService.ban_passenger(
                self.driver_token,
                self.passenger_email,
                reason="Unauthorized ban attempt",
                permanent=False
            )
        
        self.assertIn("access denied", str(context.exception).lower())

    @responses.activate
    def test_unban_passenger_success(self):
        """Test successfully unbanning a passenger as admin."""
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the banned passenger query endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.banned_passenger_email}",
            json=[self.banned_passenger],
            status=200
        )
        
        # Expected unbanned passenger data
        expected_unbanned_passenger = self.banned_passenger.copy()
        expected_unbanned_passenger.update({
            "is_banned": False,
            "ban_reason": None,
            "is_permanent_ban": False,
            "unbanned_by": self.admin_id,
            "unbanned_at": responses.matchers.ANY,
            "updated_at": responses.matchers.ANY
        })
        
        # Mock the passenger update endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.banned_passenger_id}",
            json=expected_unbanned_passenger,
            status=200
        )
        
        # Mock the bans query endpoint
        ban_record = {
            "id": f"ban_{datetime.now().timestamp()}",
            "user_id": self.banned_passenger_id,
            "user_email": self.banned_passenger_email,
            "banned_by": self.admin_id,
            "admin_email": self.admin["email"],
            "reason": "Violation of terms of service",
            "is_permanent": False,
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        
        responses.add(
            responses.GET,
            f"http://localhost:3000/bans/query?user_id={self.banned_passenger_id}&active=true",
            json=[ban_record],
            status=200
        )
        
        # Updated ban record
        updated_ban_record = ban_record.copy()
        updated_ban_record.update({
            "active": False,
            "unbanned_by": self.admin_id,
            "unbanned_at": responses.matchers.ANY
        })
        
        # Mock the ban update endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/bans/{ban_record['id']}",
            json=updated_ban_record,
            status=200
        )
        
        # Execute the unban
        result = UserService.unban_passenger(
            self.admin_token,
            self.banned_passenger_email
        )
        
        # Verify the result
        self.assertFalse(result["is_banned"])
        self.assertEqual(result["ban_reason"], None)
        self.assertFalse(result["is_permanent_ban"])
        self.assertEqual(result["unbanned_by"], self.admin_id)
        self.assertEqual(result["email"], self.banned_passenger_email)

    @responses.activate
    def test_unban_non_banned_passenger(self):
        """Test error when trying to unban a passenger that is not banned."""
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the passenger query endpoint with non-banned passenger
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.passenger_email}",
            json=[self.passenger],
            status=200
        )
        
        # Execute the unban and expect an error
        with self.assertRaises(UserServiceError) as context:
            UserService.unban_passenger(
                self.admin_token,
                self.passenger_email
            )
        
        self.assertIn("not currently banned", str(context.exception).lower())

    @responses.activate
    def test_list_banned_passengers(self):
        """Test listing banned passengers as admin."""
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Create multiple banned passengers for the list
        banned_passengers = [
            self.banned_passenger,
            {
                "id": str(uuid.uuid4()),
                "email": "banned2@example.com",
                "first_name": "Banned",
                "last_name": "User2",
                "phone": "555-333-4444",
                "user_type": UserType.PASSENGER.value,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_banned": True,
                "ban_reason": "Multiple account violations",
                "is_permanent_ban": True,
                "banned_by": self.admin_id,
                "banned_at": datetime.now().isoformat()
            }
        ]
        
        # Add some non-banned users and non-passengers to the mix
        all_users = banned_passengers + [self.passenger, self.driver]
        
        # Mock the users endpoint
        responses.add(
            responses.GET,
            "http://localhost:3000/users",
            json=all_users,
            status=200
        )
        
        # Execute the list
        result = UserService.list_banned_passengers(
            self.admin_token,
            active_only=True
        )
        
        # Verify the result
        self.assertEqual(len(result), 2)  # Should only include the two banned passengers
        
        # Check that all returned users are banned passengers
        for user in result:
            self.assertEqual(user["user_type"], UserType.PASSENGER.value)
            self.assertTrue(user["is_banned"])

    @responses.activate
    def test_get_ban_status(self):
        """Test getting the ban status for a user."""
        # Mock the user endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.banned_passenger_id}",
            json=self.banned_passenger,
            status=200
        )
        
        # Mock the bans query endpoint
        ban_record = {
            "id": f"ban_{datetime.now().timestamp()}",
            "user_id": self.banned_passenger_id,
            "user_email": self.banned_passenger_email,
            "banned_by": self.admin_id,
            "admin_email": self.admin["email"],
            "reason": "Violation of terms of service",
            "is_permanent": False,
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        
        responses.add(
            responses.GET,
            f"http://localhost:3000/bans/query?user_id={self.banned_passenger_id}&active=true",
            json=[ban_record],
            status=200
        )
        
        # Execute the get ban status
        result = UserService.get_ban_status(self.banned_passenger_id)
        
        # Verify the result
        self.assertTrue(result["is_banned"])
        self.assertEqual(result["reason"], "Violation of terms of service")
        self.assertFalse(result["is_permanent"])
        self.assertEqual(result["banned_at"], self.banned_passenger["banned_at"])
        self.assertEqual(result["banned_by_email"], self.admin["email"])

    @responses.activate
    def test_auth_validation_banned_user(self):
        """Test authentication validation for banned users."""
        # Mock the banned passenger verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.banned_passenger_id}",
            json=self.banned_passenger,
            status=200
        )
        
        # Generate a token for the banned user
        payload = {
            "user_id": self.banned_passenger_id,
            "user_type": UserType.PASSENGER.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        banned_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Expect an AuthValidationError when validating a banned user
        with self.assertRaises(AuthValidationError) as context:
            validate_user_not_banned(banned_token)
        
        self.assertIn("banned", str(context.exception).lower())

    @responses.activate
    @patch('click.confirm')
    def test_cli_ban_passenger_command(self, mock_confirm):
        """Test the CLI command for banning a passenger."""
        # Mock the token file
        self._mock_token_file(self.admin_token)
        
        # Mock the confirmation
        mock_confirm.return_value = True
        
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the passenger query endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.passenger_email}",
            json=[self.passenger],
            status=200
        )
        
        # Expected banned passenger data
        expected_banned_passenger = self.passenger.copy()
        expected_banned_passenger.update({
            "is_banned": True,
            "ban_reason": "Test ban via CLI",
            "is_permanent_ban": False,
            "banned_by": self.admin_id,
            "banned_at": responses.matchers.ANY,
            "updated_at": responses.matchers.ANY
        })
        
        # Mock the passenger update endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.passenger_id}",
            json=expected_banned_passenger,
            status=200
        )
        
        # Mock the bans collection endpoint
        responses.add(
            responses.POST,
            f"http://localhost:3000/bans",
            json={
                "id": responses.matchers.ANY,
                "user_id": self.passenger_id,
                "user_email": self.passenger_email,
                "banned_by": self.admin_id,
                "admin_email": self.admin["email"],
                "reason": "Test ban via CLI",
                "is_permanent": False,
                "created_at": responses.matchers.ANY,
                "active": True
            },
            status=201
        )
        
        # Run the CLI command
        result = self.runner.invoke(ban_passenger, [
            self.passenger_email, 
            "--reason", "Test ban via CLI"
        ])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command ran successfully
        self.assertEqual(0, result.exit_code, f"Command failed with: {result.output}")
        
        # Check output contains banned message
        self.assertIn("has been BANNED", result.output)
        self.assertIn("Test ban via CLI", result.output)
        self.assertIn("TEMPORARY", result.output)

    @responses.activate
    @patch('click.confirm')
    def test_cli_unban_passenger_command(self, mock_confirm):
        """Test the CLI command for unbanning a passenger."""
        # Mock the token file
        self._mock_token_file(self.admin_token)
        
        # Mock the confirmation
        mock_confirm.return_value = True
        
        # Mock the admin user verification endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/{self.admin_id}",
            json=self.admin,
            status=200
        )
        
        # Mock the banned passenger query endpoint
        responses.add(
            responses.GET,
            f"http://localhost:3000/users/query?email={self.banned_passenger_email}",
            json=[self.banned_passenger],
            status=200
        )
        
        # Expected unbanned passenger data
        expected_unbanned_passenger = self.banned_passenger.copy()
        expected_unbanned_passenger.update({
            "is_banned": False,
            "ban_reason": None,
            "is_permanent_ban": False,
            "unbanned_by": self.admin_id,
            "unbanned_at": responses.matchers.ANY,
            "updated_at": responses.matchers.ANY
        })
        
        # Mock the passenger update endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/users/{self.banned_passenger_id}",
            json=expected_unbanned_passenger,
            status=200
        )
        
        # Mock the bans query endpoint
        ban_record = {
            "id": f"ban_{datetime.now().timestamp()}",
            "user_id": self.banned_passenger_id,
            "user_email": self.banned_passenger_email,
            "banned_by": self.admin_id,
            "admin_email": self.admin["email"],
            "reason": "Violation of terms of service",
            "is_permanent": False,
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        
        responses.add(
            responses.GET,
            f"http://localhost:3000/bans/query?user_id={self.banned_passenger_id}&active=true",
            json=[ban_record],
            status=200
        )
        
        # Updated ban record
        updated_ban_record = ban_record.copy()
        updated_ban_record.update({
            "active": False,
            "unbanned_by": self.admin_id,
            "unbanned_at": responses.matchers.ANY
        })
        
        # Mock the ban update endpoint
        responses.add(
            responses.PUT,
            f"http://localhost:3000/bans/{ban_record['id']}",
            json=updated_ban_record,
            status=200
        )
        
        # Run the CLI command
        result = self.runner.invoke(unban_passenger, [self.banned_passenger_email])
        
        # Clean up token file
        self._clean_token_file()
        
        # Assert command ran successfully
        self.assertEqual(0, result.exit_code, f"Command failed with: {result.output}")
        
        # Check output contains unbanned message
        self.assertIn("has been UNBANNED", result.output)


if __name__ == '__main__':
    unittest.main()