# TeamHACK - Having Accelerated Conflict Kindly

## Overview
TeamHACK is a tool designed to proactively identify and address potential conflicts in teams by comparing working preferences and communication styles. By capturing individual work preferences and analyzing potential friction points, TeamHACK helps teams establish effective working norms before conflicts arise.

## Purpose
Transform potential workplace conflicts into team strengths by facilitating upfront discussions about working preferences and styles. The tool guides structured conversations that lead to better team dynamics.

#### Note: The goal  is not to create hivemind
#### The goal is to take differences that have the potential to (A) make a team complimentary and amazing, but that can also (B) create conflict if left unattended, and make sure it does the former without the latter

## Target Users
Internal team members expecting to work together for more than 2 weeks.

## Key Features
- **User Management**: Secure registration and authentication system
- **Form Templates**: Comprehensive questionnaire with multiple question types:
  - Free-form text responses
  - Forced ranking of items
  - Likert scales
  - Personality trait assessments
- **Form Comparison**: Algorithm to identify potential conflicts between two team members
- **Discussion Agenda Generation**: Automatically create focused agendas highlighting areas where team members may have conflicting preferences
- **User Dashboard**: Central hub to manage forms and comparisons

## How It Works
1. Team members register and fill out a form about their working preferences (30-120 minutes)
2. The system compares responses between two team members
3. TeamHACK generates a discussion agenda highlighting potential conflict areas
4. Team members use the agenda to discuss and establish working norms (30-120 minutes)

## Architecture Overview

### Data Architecture
The application follows a modular structure with clear separation of concerns:

```
TeamHACK/
├── src/                      # Source code
│   ├── api/                  # API endpoints
│   ├── auth/                 # Authentication system
│   ├── comparisons/          # Comparison algorithms
│   ├── config.py             # Configuration management
│   ├── db/                   # Database setup and operations
│   ├── forms/                # Form metadata and processing
│   └── models/               # Data models
├── static/                   # Static assets
│   └── css/                  # Stylesheets
├── webpages/                 # HTML templates
├── tests/                    # Unit and integration tests
└── setup/                    # Setup scripts
```

### Core Components:
1. **Database Models**:
   - `User`: Stores user authentication information
   - `CompletedForm`: Contains user form responses
   - `Comparison`: Records comparison results between two forms

2. **Comparison Engine**:
   - Analyzes different response types (Likert, ranking, text)
   - Identifies potential conflicts based on response patterns
   - Generates weighted conflict assessments

3. **Web Interface**:
   - User dashboard for form and comparison management
   - Form submission interface
   - Comparison visualization and discussion agenda

## Setup Instructions

### Prerequisites
- Python 3.9+ 
- pip (Python package manager)
- Git
- SQLite (included in Python)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/megiladi/TeamHACK.git
   cd TeamHACK
   ```

2. **Create and activate virtual environment**
   ```bash
   # On Windows
   python -m venv .venv
   .venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the root directory with the following variables:
   ```
   SECRET_KEY=your_secret_key_here
   FLASK_ENV=development
   GEMINI_API_KEY=your_gemini_api_key_here  # Optional: only needed for advanced text analysis
   ```

5. **Initialize the database**
   ```bash
   python setup/setup_database.py
   ```

6. **Run the application**
   ```bash
   python -m src.api.app
   ```

7. **Access the application**
   Open your browser and navigate to `http://127.0.0.1:5000/`

### Running Tests
```bash
python -m pytest tests/
```

## Development Guidelines

### Code Structure
- Follow modular design patterns
- Implement comprehensive error handling
- Write docstrings for all functions and classes
- Use type hints where appropriate

### Testing
- Write unit tests for all new functionality
- Run integration tests before submitting pull requests
- Maintain minimum 80% test coverage

## Future Potential Enhancements

#### Scaling and Efficiency
- Make Gemini AI key so that users without a key can use
- Clean app.py file to break out into more modular architecture (i.e., blueprints and services)
- Cloud-based storage for remote form completion
- Dynamic form handling to enable the underlying form template to be changed
- Increased capacity (50+ users)
- Support for comparing multiple team members simultaneously
- Acceleration of comparison engine for user experience

#### User Features
- Enable multiple LLM options for comparison
- Refining of comparison algorithms
- Automated discussion recommendations
- Working norms discussion resolutions logging
- Improved and increased triaging of conflicts by priority level
- Aged form flagging (12+ months)
- Ability to delete past comparisons
- Automatically reload dashboard once a form is deleted
- Navigation bar following user as they scroll down 
- Audio version for accessibility
- Ability to delete users

## License
MIT License

## Contact
For questions or support, contact mathewgiladi@gmail.com