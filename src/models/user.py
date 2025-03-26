from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from src.models.base import Base


class User(Base):
    """
    User model representing the 'users' table in the database.

    This model stores basic user information for TeamHACK.
    """
    __tablename__ = 'users'

    # Primary key for the user
    id = Column(Integer, primary_key=True)

    # Username field, must be unique and cannot be null
    username = Column(String(50), unique=True, nullable=False)

    # Email field, must be unique and cannot be null
    email = Column(String(120), unique=True, nullable=False)

    # Relationship to link users to their completed forms
    completed_forms = relationship("CompletedForm", back_populates="user")

    def __repr__(self):
        """
        Provide a string representation of the User object.

        Returns:
            str: A string containing the user's id and username.
        """
        return f"<User(id={self.id}, username='{self.username}')>"
