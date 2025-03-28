import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.base import Base
import src.models.user  # Import to ensure models are registered
import src.models.completed_form
import src.models.comparison

# Get the base directory of your project (2 levels up from this file)
# Assuming db_setup.py is in src/db/db_setup.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check if we're in testing mode
testing = os.environ.get('TESTING') == 'True'

# Use environment variable with fallback to a default location in project root
DB_PATH = os.environ.get('TEAMHACK_DB_PATH', os.path.join(BASE_DIR, 'teamhack.db'))

# Use in-memory database for testing, configured path otherwise
if testing:
    engine = create_engine('sqlite:///:memory:')
else:
    engine = create_engine(f'sqlite:///{DB_PATH}')
    print(f"Database location: {DB_PATH}")  # Helpful for debugging

# Create a session factory
Session = sessionmaker(bind=engine)

# Function to initialize the database
def init_db():
    Base.metadata.create_all(engine)