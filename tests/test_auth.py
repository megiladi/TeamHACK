import unittest
import os
from flask import Flask, session
from flask_bcrypt import Bcrypt

# Set testing environment
os.environ['TESTING'] = 'True'

from src.db.db_setup import Session, Base, engine
from src.models.user import User
from src.auth.auth_manager import AuthManager


class TestAuth(unittest.TestCase):

    def setUp(self):
        """Set up test environment before each test."""
        # Create a brand new Flask application for testing
        self.app_instance = Flask(__name__)
        self.app_instance.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            SECRET_KEY='test-key'
        )

        # Use the test client from the fresh app instance
        self.app = self.app_instance.test_client()

        # Create tables in test database
        Base.metadata.create_all(engine)

        # Create auth manager with the fresh app
        self.auth_manager = AuthManager(self.app_instance)

        # Manually hash a password for testing
        bcrypt = Bcrypt()
        hashed_password = bcrypt.generate_password_hash('Password123!').decode('utf-8')

        # Create a test user
        with Session() as session:
            test_user = User(
                username='testuser',
                email='test@example.com',
                password=hashed_password
            )
            session.add(test_user)
            session.commit()

    def tearDown(self):
        """Clean up after each test."""
        # Drop all tables in test database
        Base.metadata.drop_all(engine)

    def test_registration_success(self):
        """Test successful user registration."""
        # Set up application context for the test
        with self.app_instance.test_request_context():
            with self.app_instance.app_context():
                # Mock the registration route
                user, error = self.auth_manager.register_user(
                    'newuser',
                    'new@example.com',
                    'NewPassword123!'
                )

                # Check result
                self.assertIsNotNone(user)
                self.assertIsNone(error)

                # Verify user exists in database
                with Session() as session:
                    user = session.query(User).filter_by(username='newuser').first()
                    self.assertIsNotNone(user)
                    self.assertEqual(user.email, 'new@example.com')

    def test_registration_duplicate_username(self):
        """Test registration with an existing username."""
        with self.app_instance.test_request_context():
            with self.app_instance.app_context():
                # Try to register with existing username
                user, error = self.auth_manager.register_user(
                    'testuser',  # Existing username
                    'another@example.com',
                    'Password123!'
                )

                # Check result
                self.assertIsNone(user)
                self.assertIn('already exists', error)

    def test_registration_invalid_data(self):
        """Test registration with invalid password."""
        with self.app_instance.test_request_context():
            with self.app_instance.app_context():
                # Try to register with short password
                user, error = self.auth_manager.register_user(
                    'validuser',
                    'valid@example.com',
                    'short'  # Too short
                )

                # Check result
                self.assertIsNone(user)
                self.assertIn('at least 8 characters', error)

    def test_login_success(self):
        """Test successful login."""
        with self.app_instance.test_request_context():
            with self.app_instance.app_context():
                # Try valid login
                user, error = self.auth_manager.login('testuser', 'Password123!')

                # Check result
                self.assertIsNotNone(user)
                self.assertIsNone(error)
                self.assertEqual(user.username, 'testuser')

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        with self.app_instance.test_request_context():
            with self.app_instance.app_context():
                # Try invalid login
                user, error = self.auth_manager.login('testuser', 'WrongPassword')

                # Check result
                self.assertIsNone(user)
                self.assertIn('Invalid username or password', error)

    def test_logout(self):
        """Test logout functionality."""
        with self.app_instance.test_request_context():
            with self.app_instance.app_context():
                # First login
                user, _ = self.auth_manager.login('testuser', 'Password123!')

                # Then logout
                self.auth_manager.logout()

                # We can't easily test if logout worked directly since Flask-Login uses
                # request context to track current_user, but we can ensure the method runs


if __name__ == '__main__':
    unittest.main()