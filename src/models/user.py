from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from src.models.base import Base


class User(UserMixin, Base):
    """
    User model representing the 'users' table in the database.

    This model stores basic user information for TeamHACK and supports Flask-Login.
    """
    __tablename__ = 'users'

    # Primary key for the user
    id = Column(Integer, primary_key=True)

    # Username field, must be unique and cannot be null
    username = Column(String(50), unique=True, nullable=False)

    # Email field, must be unique and cannot be null
    email = Column(String(120), unique=True, nullable=False)

    # Password field for authentication
    password = Column(String(255), nullable=False)

    # Relationship to link users to their completed forms
    completed_forms = relationship("CompletedForm", back_populates="user")

    def is_authenticated(self):
        """
        Check if the user is authenticated.

        Returns:
            bool: Always True for authenticated users
        """
        return True

    def is_active(self):
        """
        Check if the user's account is active.

        Returns:
            bool: Always True in this implementation
        """
        return True

    def is_anonymous(self):
        """
        Check if the user is an anonymous user.

        Returns:
            bool: Always False for authenticated users
        """
        return False

    def get_id(self):
        """
        Get the user's ID for Flask-Login.

        Returns:
            str: User's ID as a string
        """
        return str(self.id)

    def __repr__(self):
        """
        Provide a string representation of the User object.

        Returns:
            str: A string containing the user's id and username.
        """
        return f"<User(id={self.id}, username='{self.username}')>"