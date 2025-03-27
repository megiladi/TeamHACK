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
        Register a new user in the database.

        Args:
            username (str): Chosen username
            email (str): User's email address
            password (str): User's password (will be hashed)

        Returns:
            User or None: Created user object or None if registration fails
        """
        # Hash the password
        hashed_password = self.bcrypt.generate_password_hash(password).decode('utf-8')

        with Session() as session:
            try:
                # Check if username or email already exists
                existing_user = (session.query(User)
                                 .filter((User.username == username) | (User.email == email))
                                 .first())

                if existing_user:
                    return None  # User already exists

                # Create new user
                new_user = User(
                    username=username,
                    email=email,
                    password=hashed_password
                )

                session.add(new_user)
                session.commit()

                return new_user

            except Exception as e:
                session.rollback()
                print(f"Registration error: {e}")
                return None

    def login(self, username, password):
        """
        Authenticate a user.

        Args:
            username (str): User's username
            password (str): User's password

        Returns:
            User or None: Authenticated user or None if login fails
        """
        with Session() as session:
            user = session.query(User).filter_by(username=username).first()

            if user and self.bcrypt.check_password_hash(user.password, password):
                login_user(user)
                return user

            return None

    def logout(self):
        """
        Log out the current user.
        """
        logout_user()