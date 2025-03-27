import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from src.models.user import User
from src.db.db_setup import Session


class AuthManager:
    def __init__(self, app):
        """
        Initialize authentication components for the application.

        Args:
            app (Flask): The Flask application instance
        """
        # Initialize login manager
        self.login_manager = LoginManager()
        self.login_manager.init_app(app)
        self.login_manager.login_view = 'login'  # Specify the login route

        # Initialize password hashing
        self.bcrypt = Bcrypt(app)

        # Track failed login attempts
        self.failed_login_attempts = {}
        self.last_attempt_time = {}

        # Set up user loader
        @self.login_manager.user_loader
        def load_user(user_id):
            """
            Callback to reload the user object from the user ID stored in the session.

            Args:
                user_id (str): User ID stored in the session

            Returns:
                User or None: User object if found, else None
            """
            with Session() as session:
                return session.query(User).get(int(user_id))

    def register_user(self, username, email, password):
        """
        Register a new user in the database with password validation.

        Args:
            username (str): Chosen username
            email (str): User's email address
            password (str): User's password (will be hashed)

        Returns:
            User or None: Created user object or None if registration fails
        """
        # Validate password strength
        if len(password) < 8:
            return None, "Password must be at least 8 characters long"

        # Simple check for password complexity
        has_letters = any(c.isalpha() for c in password)
        has_numbers = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)

        if not (has_letters and (has_numbers or has_special)):
            return None, "Password must contain letters and at least numbers or special characters"

        # Hash the password
        hashed_password = self.bcrypt.generate_password_hash(password).decode('utf-8')

        with Session() as session:
            try:
                # Check if username or email already exists
                existing_user = (session.query(User)
                                 .filter((User.username == username) | (User.email == email))
                                 .first())

                if existing_user:
                    if existing_user.username == username:
                        return None, f"Username '{username}' already exists"
                    else:
                        return None, f"Email '{email}' already exists"

                # Create new user
                new_user = User(
                    username=username,
                    email=email,
                    password=hashed_password
                )

                session.add(new_user)
                session.commit()

                # Before closing the session, copy needed attributes
                user_data = {
                    "id": new_user.id,
                    "username": new_user.username,
                    "email": new_user.email
                }

                # Return the dictionary instead of the SQLAlchemy model object
                return user_data, None

            except Exception as e:
                session.rollback()
                print(f"Registration error details: {str(e)}")
                return None, f"Registration error: {str(e)}"

    def login(self, username, password):
        """
        Authenticate a user with rate limiting.

        Args:
            username (str): User's username
            password (str): User's password

        Returns:
            User or None: Authenticated user or None if login fails
        """
        import time
        from datetime import datetime, timedelta

        # Check for too many failed attempts
        current_time = datetime.now()
        if username in self.failed_login_attempts:
            # If user has failed more than 5 times
            if self.failed_login_attempts[username] >= 5:
                # Check if enough time has passed since last attempt
                if username in self.last_attempt_time:
                    time_since_last = current_time - self.last_attempt_time[username]
                    if time_since_last < timedelta(minutes=15):
                        # Account is temporarily locked
                        return None, "Too many failed attempts. Please try again later."
                    else:
                        # Reset attempts after lockout period
                        self.failed_login_attempts[username] = 0

        # Update last attempt time
        self.last_attempt_time[username] = current_time

        with Session() as session:
            user = session.query(User).filter_by(username=username).first()

            if user and self.bcrypt.check_password_hash(user.password, password):
                # Successful login - reset failed attempts
                if username in self.failed_login_attempts:
                    self.failed_login_attempts[username] = 0

                login_user(user)
                return user, None
            else:
                # Failed login - increment counter
                if username not in self.failed_login_attempts:
                    self.failed_login_attempts[username] = 1
                else:
                    self.failed_login_attempts[username] += 1

                return None, "Invalid username or password"

    def logout(self):
        """
        Log out the current user.
        """
        logout_user()

    def validate_password(self, password):
        """
        Validate password meets security requirements.

        Args:
            password (str): Password to validate

        Returns:
            tuple: (is_valid, message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"

        has_digit = any(char.isdigit() for char in password)
        has_letter = any(char.isalpha() for char in password)

        if not (has_digit and has_letter):
            return False, "Password must contain both letters and numbers"

        return True, "Password is valid"