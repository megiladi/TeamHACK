# TeamHACK Architecture

Last updated 3/24/2025

The project follows a modular structure with clear separation of concerns:

### Documentation
- `docs/setup_guide.md` - Setup instructions for new users

### Source Code (`src/`)

- **API Layer (`api/`)**
  - `__init__.py`
  - `app.py` - Main API endpoints

- **Comparison Logic  (`comparisons/`)**
  - `__init__.py`
  - `comparison.py` - Form comparison algorithms

- **Database Layer  (`db/`)**
  - `__init__.py`
  - `db_setup.py` - Database initialization

- **Data Models (`models/`)**
  - `__init__.py`
  - `user.py` - User model definition

- **Questionnaire Functionality (`questionnaires/`)**
  - `__init__.py`
  - `questionnaire.py` - Questionnaire model

- **Business Logic (`services/`)**
  - `__init__.py`
  - `user_service.py` - User-related operations

- **UI Templates (`templates/`)**
  - `__init__.py`

- **Utility Functions (`utils/`)**
  - `__init__.py`
  - `validators.py` - Input validation

- **Core Files for src**
  - `__init__.py` - Package initialization
  - `config.py` - Configuration settings

### Testing (`tests/`)
- `__init__.py`
- `test_app.py` - API tests
- `test_models.py` - Model tests
- `test_questionnaires.py` - Questionnaire tests

### Project Root Files
- `.env` - Environment variables
- `.gitignore` - Git ignore file
- `README.md` - Project overview
- `requirements.txt` - Project dependencies