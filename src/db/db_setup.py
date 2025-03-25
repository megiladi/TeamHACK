from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.user import Base as UserBase
from src.models.completed_form import Base as CompletedFormBase
from src.models.comparison import Base as ComparisonBase

# Create SQLite database engine
engine = create_engine('sqlite:///teamhack.db')

# Create a session factory
Session = sessionmaker(bind=engine)

# Function to initialize the database
def init_db():
    UserBase.metadata.create_all(engine)
    CompletedFormBase.metadata.create_all(engine)
    ComparisonBase.metadata.create_all(engine)
