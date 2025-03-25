from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Base class for all models
Base = declarative_base()


class Comparison(Base):
    """
    Comparison model representing the 'comparisons' table in the database.

    This model stores results of comparing two completed forms, including any discrepancies or aligned values.
    """
    __tablename__ = 'comparisons'

    # Primary key for each comparison entry
    id = Column(Integer, primary_key=True)

    # Foreign key linking to the first completed form being compared
    form1_id = Column(Integer, ForeignKey('completed_forms.id'), nullable=False)

    # Foreign key linking to the second completed form being compared
    form2_id = Column(Integer, ForeignKey('completed_forms.id'), nullable=False)

    # Results of the comparison (e.g., JSON string capturing discrepancies or alignment)
    result = Column(String, nullable=False)

    # Relationships to link back to the completed forms
    form1 = relationship("CompletedForm", foreign_keys=[form1_id])
    form2 = relationship("CompletedForm", foreign_keys=[form2_id])

    def __repr__(self):
        """
        Provide a string representation of the Comparison object.

        Returns:
            str: A string containing the comparison's id and associated form IDs.
        """
        return f"<Comparison(id={self.id}, form1_id={self.form1_id}, form2_id={self.form2_id})>"
