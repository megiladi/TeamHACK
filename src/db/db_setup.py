import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.base import Base
import src.models.user  # Import to ensure models are registered
import src.models.completed_form
import src.models.comparison

# Check if we're in testing mode
testing = os.environ.get('TESTING') == 'True'

# Use in-memory database for testing, SQLite database otherwise
if testing:
    engine = create_engine('sqlite:///:memory:')
else:
    engine = create_engine('sqlite:///teamhack.db')

# Create a session factory
Session = sessionmaker(bind=engine)

# Function to initialize the database
def init_db():
    Base.metadata.create_all(engine)