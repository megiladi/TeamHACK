import os
import unittest
from flask import Flask
from flask_login import login_user, logout_user, current_user
from src.auth.auth_manager import AuthManager
from src.models.user import User
from src.db.db_setup import init_db, engine, Base, Session

# Set testing environment
os.environ['TESTING'] = 'True'


class TestAuth(unittest.TestCase):
    """Test cases for authentication functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment once for all tests."""
        # Create a test Flask app
        cls.app = Flask(__name__)
        cls.app.config['SECRET_KEY'] = 'test_secret_key'
        cls.app.config['TESTING'] = True

        # Set up database
        Base.metadata.create_all(engine)

        # Initialize auth manager
        cls.auth_manager = AuthManager(cls.app)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        Base.metadata.drop_all(engine)

    def setUp(self):
        """Set up clean data for each test."""
        # Start with a clean session
        self.session = Session()

        # Clear existing users
        self.session.query(User).delete()
        self.session.commit()

        # Create an app context for testing
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Create a request context for testing
        self.request_context = self.app.test_request_context()
        self.request_context.push()

    def tearDown(self):
        """Clean up after each test."""
        self.session.close()
        self.request_context.pop()
        self.app_context.pop()

    def test_register_user(self):
        """Test user registration functionality."""
        # Test successful registration
        user_data, error = self.auth_manager.register_user(
            username="valid_user",
            email="valid@example.com",
            password="ValidPassword123!"
        )

        self.assertIsNotNone(user_data)
        self.assertIsNone(error)
        self.assertEqual(user_data["username"], "valid_user")

        # Check that user was actually created in database
        user = self.session.query(User).filter_by(username="valid_user").first()
        self.assertIsNotNone(user)

        # Test registration with weak password
        user_data, error = self.auth_manager.register_user(
            username="weak_password_user",
            email="weak@example.com",
            password="weak"
        )

        self.assertIsNone(user_data)
        self.assertIsNotNone(error)
        self.assertTrue("Password must be at least 8 characters" in error)

        # Test registration with existing username
        user_data, error = self.auth_manager.register_user(
            username="valid_user",  # Already exists
            email="another@example.com",
            password="AnotherValidPassword123!"
        )

        self.assertIsNone(user_data)
        self.assertIsNotNone(error)
        self.assertTrue("already exists" in error)

        # Test registration with existing email
        user_data, error = self.auth_manager.register_user(
            username="another_user",
            email="valid@example.com",  # Already exists
            password="AnotherValidPassword123!"
        )

        self.assertIsNone(user_data)
        self.assertIsNotNone(error)
        self.assertTrue("already exists" in error)

    def test_login(self):
        """Test login functionality."""
        # First register a user
        self.auth_manager.register_user(
            username="login_test_user",
            email="login@example.com",
            password="LoginTestPassword123!"
        )

        # Test successful login
        user, error = self.auth_manager.login(
            username="login_test_user",
            password="LoginTestPassword123!"
        )

        self.assertIsNotNone(user)
        self.assertIsNone(error)
        self.assertEqual(user.username, "login_test_user")

        # Test login with incorrect password
        user, error = self.auth_manager.login(
            username="login_test_user",
            password="WrongPassword123!"
        )

        self.assertIsNone(user)
        self.assertIsNotNone(error)
        self.assertTrue("Invalid username or password" in error)

        # Test login with non-existent username
        user, error = self.auth_manager.login(
            username="nonexistent_user",
            password="SomePassword123!"
        )

        self.assertIsNone(user)
        self.assertIsNotNone(error)
        self.assertTrue("Invalid username or password" in error)

    def test_validate_password(self):
        """Test password validation functionality."""
        # Valid password
        is_valid, message = self.auth_manager.validate_password("ValidPassword123!")
        self.assertTrue(is_valid)
        self.assertEqual(message, "Password is valid")

        # Too short
        is_valid, message = self.auth_manager.validate_password("Short1")
        self.assertFalse(is_valid)
        self.assertTrue("at least 8 characters" in message)

        # Missing digit
        is_valid, message = self.auth_manager.validate_password("OnlyLetters")
        self.assertFalse(is_valid)
        self.assertTrue("both letters and numbers" in message)

        # Missing letter
        is_valid, message = self.auth_manager.validate_password("12345678")
        self.assertFalse(is_valid)
        self.assertTrue("both letters and numbers" in message)

    def test_logout(self):
        """Test logout functionality."""
        # First register and login a user
        self.auth_manager.register_user(
            username="logout_test_user",
            email="logout@example.com",
            password="LogoutTestPassword123!"
        )

        user, _ = self.auth_manager.login(
            username="logout_test_user",
            password="LogoutTestPassword123!"
        )

        # Verify user is logged in
        self.assertTrue(hasattr(current_user, 'id'))
        self.assertEqual(current_user.username, "logout_test_user")

        # Logout
        self.auth_manager.logout()

        # Verify user is logged out
        self.assertTrue(current_user.is_anonymous)

    def test_rate_limiting(self):
        """Test login rate limiting functionality."""
        # Register a user
        self.auth_manager.register_user(
            username="rate_limit_user",
            email="rate@example.com",
            password="RateLimitTest123!"
        )

        # Attempt login with wrong password multiple times
        for i in range(5):
            user, error = self.auth_manager.login(
                username="rate_limit_user",
                password="WrongPassword" + str(i)
            )
            self.assertIsNone(user)

        # After 5 failed attempts, the next login attempt should be rate-limited
        user, error = self.auth_manager.login(
            username="rate_limit_user",
            password="WrongPasswordAgain"
        )

        self.assertIsNone(user)
        self.assertTrue("Too many failed attempts" in error)

        # Even correct password should be rejected during lockout
        user, error = self.auth_manager.login(
            username="rate_limit_user",
            password="RateLimitTest123!"
        )

        self.assertIsNone(user)
        self.assertTrue("Too many failed attempts" in error)


if __name__ == '__main__':
    unittest.main()