from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Create a base class for declarative models
Base = declarative_base()


class CompletedForm(Base):
    """
    CompletedForm model representing the 'completed_forms' table in the database.

    This model stores user-submitted, completed forms and their content for TeamHACK.
    It allows for flexible storage of various question types and responses.
    """
    __tablename__ = 'completed_forms'

    # Primary key for each completed form
    id = Column(Integer, primary_key=True)

    # Foreign key linking this form to a specific user
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Content of the completed form, stored as JSON string
    # This allows for flexible storage of different question types (e.g., Likert scales, rankings, free text)
    content = Column(String, nullable=False)

    # Relationship to link this completed form back to its user
    # This enables easy access to the user who submitted this form
    user = relationship("User", back_populates="completed_forms")

    def __repr__(self):
        """
        Provide a string representation of the CompletedForm object.

        This method is useful for debugging, logging, and when printing CompletedForm objects.

        Returns:
            str: A string containing the completed form's id and associated user_id.
        """
        return f"<CompletedForm(id={self.id}, user_id={self.user_id})>"
