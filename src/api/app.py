"""
TeamHACK Application - Main Flask Application
--------------------------------------------
This module contains the main Flask application for TeamHACK (Having Accelerated Conflict Kindly).
It provides routes for authentication, form management, and comparing team member preferences.
"""

import logging
import os
import json
from flask import Flask, request, jsonify, render_template, redirect
from flask_login import login_required, current_user, login_user
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# Import models and services
from src.models.user import User
from src.models.completed_form import CompletedForm
from src.models.comparison import Comparison
from src.db.db_setup import init_db, Session
from src.comparisons.comparison_engine import ComparisonEngine
from src.auth.auth_manager import AuthManager


# -------------------------
# Application Setup
# -------------------------

def setup_logging():
    """Configure application logging."""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'teamhack.log')),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


# Configure logging
logger = setup_logging()
logger.info("Starting TeamHACK application")


# Initialize Flask application
def create_app():
    """Create and configure the Flask application."""
    template_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'webpages'))
    app = Flask(__name__, template_folder=template_folder)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['ENV'] = os.getenv('FLASK_ENV', 'development')
    app.jinja_env.autoescape = True
    return app


app = create_app()

# Initialize database
init_db()
logger.info("Database tables initialized")

# Path to form.html for form metadata
form_html_path = os.path.join(os.path.dirname(__file__), '..', 'webpages', 'form.html')

# Initialize the comparison engine with the form path
comparison_engine = ComparisonEngine(form_html_path)

# Initialize Authentication Manager
auth_manager = AuthManager(app)


# -------------------------
# Helper Functions
# -------------------------

def handle_api_error(error, status_code=500):
    """Standard error handler for API responses."""
    logger.error(f"API error: {str(error)}", exc_info=True)
    return jsonify({"error": f"Server error: {str(error)}"}), status_code


def validate_form_ownership(form_id):
    """
    Validate that a form exists and belongs to the current user.

    Args:
        form_id: The ID of the form to check

    Returns:
        tuple: (form, None) if valid, (None, error_response) if invalid
    """
    with Session() as session:
        form = session.query(CompletedForm).get(form_id)

        if not form:
            return None, (jsonify({"error": f"Form with ID {form_id} not found"}), 404)

        if form.user_id != current_user.id:
            logger.warning(
                f"User {current_user.username} attempted to access form {form_id} belonging to user {form.user_id}")
            return None, (jsonify({"error": "You don't have permission to access this form"}), 403)

        return form, None

@app.route('/', methods=['GET'])
def index():
    """Route for the root URL, redirects appropriately based on authentication."""
    if current_user.is_authenticated:
        return redirect('/dashboard')
    else:
        return redirect('/login')


# -------------------------
# Authentication Routes
# -------------------------

@app.route('/register', methods=['POST'])
def register():
    """User registration route."""
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # Validate input
        if not all([username, email, password]):
            return jsonify({"error": "Missing required fields"}), 400

        # Attempt to register the user
        user_data, error_msg = auth_manager.register_user(username, email, password)

        if user_data:
            return jsonify({
                "message": "User registered successfully",
                "user_id": user_data["id"]
            }), 201
        else:
            return jsonify({"error": error_msg}), 409

    except Exception as e:
        return handle_api_error(e)


@app.route('/login', methods=['POST'])
def login():
    """User login route."""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        logger.debug(f"Login attempt for username: {username}")

        # Validate input
        if not all([username, password]):
            return jsonify({"error": "Missing username or password"}), 400

        # Attempt to log in the user
        user, error_msg = auth_manager.login(username, password)

        if user:
            logger.info(f"Login successful for {username}, user_id={user.id}")
            return jsonify({
                "message": "Login successful",
                "user_id": user.id,
                "username": user.username
            }), 200
        else:
            logger.warning(f"Login failed for {username}: {error_msg}")
            return jsonify({"error": error_msg}), 401

    except Exception as e:
        return handle_api_error(e)


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """User logout route."""
    try:
        auth_manager.logout()
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        return handle_api_error(e)


@app.route('/login', methods=['GET'])
def login_page():
    """Render the login page."""
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('login.html')


@app.route('/register', methods=['GET'])
def register_page():
    """Render the registration page."""
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('register.html')


@app.route('/profile', methods=['GET'])
@login_required
def profile():
    """User profile page - example of a protected route that requires login."""
    return jsonify({
        "message": "You are logged in!",
        "user_id": current_user.id,
        "username": current_user.username
    }), 200


# -------------------------
# User Routes
# -------------------------

@app.route('/users', methods=['POST'])
def create_user():
    """Create a new user."""
    try:
        data = request.json
        logger.debug(f"User creation request received: {data}")

        # Validate input
        if not data:
            return jsonify({"error": "No data provided"}), 400

        if 'username' not in data:
            return jsonify({"error": "Missing required field: username"}), 400

        if 'email' not in data:
            return jsonify({"error": "Missing required field: email"}), 400

        # Validate email format
        if '@' not in data['email']:
            return jsonify({"error": "Invalid email format"}), 400

        # Create a temporary password (properly hashed)
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        temp_password = bcrypt.generate_password_hash("temppassword123").decode('utf-8')

        new_user = User(
            username=data['username'],
            email=data['email'],
            password=temp_password
        )

        with Session() as session:
            # Check if username already exists
            existing_username = session.query(User).filter_by(username=data['username']).first()
            if existing_username:
                return jsonify({"error": f"Username '{data['username']}' already exists"}), 409

            # Check if email already exists
            existing_email = session.query(User).filter_by(email=data['email']).first()
            if existing_email:
                return jsonify({"error": f"Email '{data['email']}' already exists"}), 409

            session.add(new_user)
            session.commit()
            return jsonify({"message": "User created", "id": new_user.id}), 201
    except Exception as e:
        return handle_api_error(e)


@app.route('/users', methods=['GET'])
def get_users():
    """Get a list of all users."""
    with Session() as session:
        try:
            users = session.query(User).all()
            user_list = [{"id": u.id, "username": u.username, "email": u.email} for u in users]
            return jsonify(user_list), 200
        except Exception as e:
            return handle_api_error(e)


@app.route('/api/current_user', methods=['GET'])
@login_required
def get_current_user():
    """Get information about the currently logged-in user."""
    try:
        return jsonify({
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email
        }), 200
    except Exception as e:
        return handle_api_error(e)


@app.route('/users/username/<string:username>', methods=['GET'])
def get_user_by_username(username):
    """
    Get user details by username.

    Args:
        username: The username to look up

    Returns:
        JSON with user details or error
    """
    if not username:
        return jsonify({"error": "Username parameter is required"}), 400

    with Session() as session:
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return jsonify({"error": f"User '{username}' not found"}), 404

            # Return user details
            return jsonify({
                "id": user.id,
                "username": user.username,
                "email": user.email
            }), 200
        except Exception as e:
            return handle_api_error(e)


# -------------------------
# Form Routes
# -------------------------

@app.route('/fill_form', methods=['GET'])
def fill_form():
    """Render the form submission page."""
    try:
        return render_template('form.html')
    except Exception as e:
        logger.error(f"Error rendering form template: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/completed_forms', methods=['POST'])
@login_required
def create_completed_form():
    """Submit a new completed form for the current user."""
    try:
        # Convert form data to a dictionary
        data = request.form.to_dict()

        # Validate that form isn't empty
        if not data:
            return jsonify({"error": "Form submission cannot be empty"}), 400

        # Validate that there's at least one actual question/answer field
        question_fields = [key for key in data.keys() if key != 'user_id' and not key.startswith('_')]
        if not question_fields:
            return jsonify({"error": "Form must contain at least one question response"}), 400

        # Use the current logged-in user
        user_id = current_user.id

        # Convert form data to a JSON string for storage
        content_json = json.dumps(data)

        # Create the new form object
        new_form = CompletedForm(user_id=user_id, content=content_json)

        # Add to database
        with Session() as session:
            session.add(new_form)
            session.commit()
            logger.info(f"Form submitted successfully by user {current_user.username}")
            return jsonify({"message": "Form submitted successfully", "id": new_form.id}), 201
    except Exception as e:
        return handle_api_error(e)


@app.route('/completed_forms', methods=['GET'])
def get_completed_forms():
    """Get a list of all completed forms."""
    with Session() as session:
        try:
            forms = session.query(CompletedForm).all()
            form_list = [{"id": f.id, "user_id": f.user_id, "content": f.content} for f in forms]
            return jsonify(form_list), 200
        except Exception as e:
            return handle_api_error(e)


@app.route('/api/user_forms', methods=['GET'])
@login_required
def get_user_forms():
    """Get all forms for the currently logged-in user."""
    with Session() as session:
        try:
            # Get forms for the current user
            forms = session.query(CompletedForm).filter_by(user_id=current_user.id).all()

            # Format the response
            form_list = []
            for form in forms:
                form_data = {
                    "id": form.id,
                    "user_id": form.user_id,
                    # Parse the form content if it's stored as JSON
                    "content": json.loads(form.content) if isinstance(form.content, str) else form.content
                }
                form_list.append(form_data)

            return jsonify(form_list), 200
        except Exception as e:
            return handle_api_error(e)


@app.route('/view_form/<int:form_id>', methods=['GET'])
@login_required
def view_form(form_id):
    """Route to view a specific form."""
    with Session() as session:
        try:
            # Validate form ownership
            form, error_response = validate_form_ownership(form_id)
            if error_response:
                return error_response

            # Get the user who owns the form
            user = session.query(User).get(form.user_id)

            # Parse form content if it's stored as a JSON string
            form_content = json.loads(form.content) if isinstance(form.content, str) else form.content

            # Either return JSON data or render a template
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    "id": form.id,
                    "user": user.username,
                    "content": form_content
                }), 200
            else:
                return render_template(
                    'view_form.html',
                    form_id=form.id,
                    username=user.username,
                    form_content=form_content
                )
        except Exception as e:
            return handle_api_error(e)


@app.route('/forms/user/<string:username>/latest', methods=['GET'])
def get_latest_form_by_username(username):
    """
    Get the most recent form submitted by a user.

    Args:
        username: The username to look up

    Returns:
        JSON with the latest form or error
    """
    if not username:
        return jsonify({"error": "Username parameter is required"}), 400

    with Session() as session:
        try:
            # Find the user
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return jsonify({"error": f"User '{username}' not found"}), 404

            # Get their most recent form
            latest_form = session.query(CompletedForm).filter_by(user_id=user.id).order_by(
                CompletedForm.id.desc()).first()
            if not latest_form:
                return jsonify({"error": f"No forms found for user '{username}'"}), 404

            # Return the form
            return jsonify({
                "id": latest_form.id,
                "user_id": latest_form.user_id,
                "content": latest_form.content
            }), 200
        except Exception as e:
            return handle_api_error(e)


@app.route('/edit_form/<int:form_id>', methods=['GET'])
@login_required
def edit_form(form_id):
    """Route to edit a specific form."""
    with Session() as session:
        try:
            # Validate form ownership
            form, error_response = validate_form_ownership(form_id)
            if error_response:
                return error_response

            # Get the user who owns the form
            user = session.query(User).get(form.user_id)

            # Parse form content if it's stored as a JSON string
            form_content = json.loads(form.content) if isinstance(form.content, str) else form.content

            # Render the edit form template with pre-filled data
            return render_template(
                'edit_form.html',
                form_id=form.id,
                username=user.username,
                form_content=form_content
            )
        except Exception as e:
            return handle_api_error(e)


@app.route('/api/forms/<int:form_id>', methods=['PUT', 'POST'])
@login_required
def update_form(form_id):
    """API route to update an existing form."""
    logger.debug(f"API request to update form {form_id} by user {current_user.username}")

    try:
        # Convert form data to a dictionary
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()

        with Session() as session:
            # Retrieve the form from the database
            form = session.query(CompletedForm).get(form_id)

            if not form:
                logger.warning(f"Form with ID {form_id} not found")
                return jsonify({"error": f"Form with ID {form_id} not found"}), 404

            # Check if the form belongs to the current user
            if form.user_id != current_user.id:
                logger.warning(
                    f"User {current_user.username} attempted to update form {form_id} belonging to user {form.user_id}")
                return jsonify({"error": "You don't have permission to update this form"}), 403

            # Convert form data to a JSON string for storage
            content_json = json.dumps(data)

            # Update the form content and ensure it's committed
            form.content = content_json
            session.add(form)  # Explicitly add the modified object
            session.commit()

            logger.info(f"Form {form_id} successfully updated by user {current_user.username}")
            return jsonify({"message": f"Form updated successfully"}), 200

    except Exception as e:
        return handle_api_error(e)


@app.route('/api/forms/<int:form_id>', methods=['DELETE'])
@login_required
def delete_form(form_id):
    """API route to delete a form belonging to the current user."""
    logger.debug(f"API request to delete form {form_id} by user {current_user.username}")

    with Session() as session:
        try:
            # Validate form ownership
            form, error_response = validate_form_ownership(form_id)
            if error_response:
                return error_response

            # Delete the form
            session.delete(form)
            session.commit()
            logger.info(f"Form {form_id} successfully deleted by user {current_user.username}")

            return jsonify({"message": f"Form deleted successfully"}), 200
        except Exception as e:
            session.rollback()
            return handle_api_error(e)


# -------------------------
# Comparison Routes
# -------------------------
@app.route('/comparisons', methods=['POST'])
def create_comparison():
    """Create a new comparison between two forms."""
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Check required fields
        required_fields = ['form1_id', 'form2_id', 'result']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate IDs
        try:
            form1_id = int(data['form1_id'])
            form2_id = int(data['form2_id'])
        except (ValueError, TypeError):
            return jsonify({"error": "form1_id and form2_id must be valid integers"}), 400

        # Check if forms exist
        with Session() as session:
            form1 = session.query(CompletedForm).get(form1_id)
            if not form1:
                return jsonify({"error": f"Form with ID {form1_id} not found"}), 404

            form2 = session.query(CompletedForm).get(form2_id)
            if not form2:
                return jsonify({"error": f"Form with ID {form2_id} not found"}), 404

        # Validate result is valid JSON
        try:
            json.loads(data['result'])
        except json.JSONDecodeError:
            return jsonify({"error": "Result field must contain valid JSON"}), 400

        new_comparison = Comparison(form1_id=form1_id, form2_id=form2_id, result=data['result'])

        with Session() as session:
            session.add(new_comparison)
            session.commit()
            return jsonify({"message": "Comparison created", "id": new_comparison.id}), 201
    except Exception as e:
        return handle_api_error(e)


@app.route('/compare_users/ids', methods=['POST'])
def compare_users_by_ids():
    """
    Compare the most recent forms from two users identified by their IDs.

    Request body:
    {
        "user1_id": <int>,
        "user2_id": <int>
    }

    Returns:
        JSON response with comparison results
    """
    try:
        data = request.json

        # Validate request
        if not data or 'user1_id' not in data or 'user2_id' not in data:
            return jsonify({"error": "Missing user IDs"}), 400

        user1_id = int(data['user1_id'])
        user2_id = int(data['user2_id'])

        # Retrieve users and their most recent forms
        with Session() as session:
            user1 = session.query(User).get(user1_id)
            user2 = session.query(User).get(user2_id)

            if not user1 or not user2:
                return jsonify({"error": "One or both users not found"}), 404

            # Get most recent form for each user
            form1 = session.query(CompletedForm).filter_by(user_id=user1_id).order_by(CompletedForm.id.desc()).first()
            form2 = session.query(CompletedForm).filter_by(user_id=user2_id).order_by(CompletedForm.id.desc()).first()

            if not form1 or not form2:
                return jsonify({"error": "One or both users have no completed forms"}), 404

            # Run comparison using the engine
            comparison_result = comparison_engine.compare_forms(form1.content, form2.content)

            # Create a new comparison record
            result_json = json.dumps(comparison_result)
            new_comparison = Comparison(
                form1_id=form1.id,
                form2_id=form2.id,
                result=result_json
            )

            session.add(new_comparison)
            session.commit()

            return jsonify({
                "message": "Comparison created successfully",
                "id": new_comparison.id,
                "users": {
                    "user1_id": user1_id,
                    "user2_id": user2_id
                },
                "result": comparison_result
            }), 201
    except Exception as e:
        return handle_api_error(e)


@app.route('/compare_users/usernames', methods=['POST'])
def compare_users_by_usernames():
    """
    Compare the most recent forms from two users identified by their usernames.

    Request body:
    {
        "username1": <string>,
        "username2": <string>
    }

    Returns:
        JSON response with comparison results
    """
    try:
        data = request.json

        # Validate request
        if not data or 'username1' not in data or 'username2' not in data:
            return jsonify({"error": "Missing usernames"}), 400

        username1 = data['username1']
        username2 = data['username2']

        # Retrieve users and their most recent forms
        with Session() as session:
            user1 = session.query(User).filter_by(username=username1).first()
            user2 = session.query(User).filter_by(username=username2).first()

            if not user1 or not user2:
                return jsonify({"error": "One or both users not found"}), 404

            # Get most recent form for each user
            form1 = session.query(CompletedForm).filter_by(user_id=user1.id).order_by(CompletedForm.id.desc()).first()
            form2 = session.query(CompletedForm).filter_by(user_id=user2.id).order_by(CompletedForm.id.desc()).first()

            if not form1 or not form2:
                return jsonify({"error": "One or both users have no completed forms"}), 404

            # Run comparison using the engine
            comparison_result = comparison_engine.compare_forms(form1.content, form2.content)

            # Create a new comparison record
            result_json = json.dumps(comparison_result)
            new_comparison = Comparison(
                form1_id=form1.id,
                form2_id=form2.id,
                result=result_json
            )

            session.add(new_comparison)
            session.commit()

            return jsonify({
                "message": "Comparison created successfully",
                "id": new_comparison.id,
                "users": {
                    "username1": username1,
                    "username2": username2
                },
                "result": comparison_result
            }), 201
    except Exception as e:
        return handle_api_error(e)


@app.route('/comparisons', methods=['GET'])
def get_comparisons():
    """Get a list of all comparisons."""
    with Session() as session:
        try:
            comparisons = session.query(Comparison).all()
            comparison_list = [
                {
                    "id": c.id,
                    "form1_id": c.form1_id,
                    "form2_id": c.form2_id,
                    "result": c.result
                }
                for c in comparisons
            ]
            return jsonify(comparison_list), 200
        except Exception as e:
            return handle_api_error(e)


@app.route('/comparisons/users/ids/<int:user1_id>/<int:user2_id>', methods=['GET'])
def get_comparison_by_user_ids(user1_id, user2_id):
    """
    Retrieve the most recent comparison between two users identified by their IDs.

    Args:
        user1_id: First user's ID
        user2_id: Second user's ID

    Returns:
        JSON with comparison results
    """
    with Session() as session:
        try:
            # Find the users
            user1 = session.query(User).get(user1_id)
            user2 = session.query(User).get(user2_id)

            if not user1 or not user2:
                return jsonify({"error": "One or both users not found"}), 404

            # Find the most recent forms for each user
            form1 = session.query(CompletedForm).filter_by(user_id=user1_id).order_by(CompletedForm.id.desc()).first()
            form2 = session.query(CompletedForm).filter_by(user_id=user2_id).order_by(CompletedForm.id.desc()).first()

            if not form1 or not form2:
                return jsonify({"error": "One or both users have no completed forms"}), 404

            # Find the most recent comparison between these forms
            comparison = session.query(Comparison) \
                .filter(
                ((Comparison.form1_id == form1.id) & (Comparison.form2_id == form2.id)) |
                ((Comparison.form1_id == form2.id) & (Comparison.form2_id == form1.id))
            ) \
                .order_by(Comparison.id.desc()) \
                .first()

            if not comparison:
                return jsonify({"error": "No comparison found between these users"}), 404

            # Process the comparison result
            result = json.loads(comparison.result)

            return jsonify({
                "id": comparison.id,
                "users": {
                    "user1": {"id": user1.id, "username": user1.username},
                    "user2": {"id": user2.id, "username": user2.username}
                },
                "result": result
            }), 200
        except Exception as e:
            return handle_api_error(e)


@app.route('/comparisons/users/usernames/<string:username1>/<string:username2>', methods=['GET'])
def get_comparison_by_usernames(username1, username2):
    """
    Retrieve the most recent comparison between two users identified by their usernames.

    Args:
        username1: First user's username
        username2: Second user's username

    Returns:
        JSON with comparison results
    """
    with Session() as session:
        try:
            # Find users by username
            user1 = session.query(User).filter_by(username=username1).first()
            user2 = session.query(User).filter_by(username=username2).first()

            if not user1 or not user2:
                return jsonify({"error": "One or both users not found"}), 404

            # Find the most recent forms for each user
            form1 = session.query(CompletedForm).filter_by(user_id=user1.id).order_by(CompletedForm.id.desc()).first()
            form2 = session.query(CompletedForm).filter_by(user_id=user2.id).order_by(CompletedForm.id.desc()).first()

            if not form1 or not form2:
                return jsonify({"error": "One or both users have no completed forms"}), 404

            # Find the most recent comparison between these forms
            comparison = session.query(Comparison) \
                .filter(
                ((Comparison.form1_id == form1.id) & (Comparison.form2_id == form2.id)) |
                ((Comparison.form1_id == form2.id) & (Comparison.form2_id == form1.id))
            ) \
                .order_by(Comparison.id.desc()) \
                .first()

            if not comparison:
                return jsonify({"error": "No comparison found between these users"}), 404

            # Process the comparison result
            result = json.loads(comparison.result)

            return jsonify({
                "id": comparison.id,
                "users": {
                    "user1": {"id": user1.id, "username": user1.username},
                    "user2": {"id": user2.id, "username": user2.username}
                },
                "result": result
            }), 200
        except Exception as e:
            return handle_api_error(e)


@app.route('/api/user_comparisons', methods=['GET'])
@login_required
def get_user_comparisons():
    """Get comparisons involving the current user."""
    logger.debug(f"Fetching comparisons for user {current_user.username}")

    with Session() as session:
        try:
            # First get all forms by this user
            user_forms = session.query(CompletedForm).filter_by(user_id=current_user.id).all()

            if not user_forms:
                logger.info(f"No forms found for user {current_user.username}")
                return jsonify([]), 200

            # Get form IDs
            form_ids = [form.id for form in user_forms]

            # Find comparisons involving these forms
            comparisons = session.query(Comparison).filter(
                (Comparison.form1_id.in_(form_ids)) |
                (Comparison.form2_id.in_(form_ids))
            ).all()

            results = []
            for comp in comparisons:
                try:
                    form1 = session.get(CompletedForm, comp.form1_id)
                    form2 = session.get(CompletedForm, comp.form2_id)

                    if not form1 or not form2:
                        continue

                    user1 = session.get(User, form1.user_id)
                    user2 = session.get(User, form2.user_id)

                    if not user1 or not user2:
                        continue

                    results.append({
                        "id": comp.id,
                        "user1": user1.username,
                        "user2": user2.username,
                        "date": comp.id  # Using ID as proxy for date (add a date field later)
                    })
                except Exception as e:
                    logger.error(f"Error processing comparison {comp.id}: {str(e)}")

            logger.info(f"Found {len(results)} comparisons for user {current_user.username}")
            return jsonify(results), 200

        except Exception as e:
            return handle_api_error(e)


@app.route('/comparisons/<int:comparison_id>/view', methods=['GET'])
def view_comparison_page(comparison_id):
    """Render the comparison visualization page."""
    with Session() as session:
        try:
            logger.debug(f"Fetching comparison with ID: {comparison_id}")

            comparison = session.query(Comparison).get(comparison_id)
            if not comparison:
                return jsonify({"error": f"Comparison with ID {comparison_id} not found"}), 404

            # Check if forms exist
            form1 = session.query(CompletedForm).get(comparison.form1_id)
            form2 = session.query(CompletedForm).get(comparison.form2_id)

            if not form1 or not form2:
                return jsonify({"error": "One or both forms in this comparison no longer exist"}), 404

            # Check if users exist
            user1 = session.query(User).get(form1.user_id)
            user2 = session.query(User).get(form2.user_id)

            if not user1 or not user2:
                return jsonify({"error": "One or both users in this comparison no longer exist"}), 404

            # Parse JSON strings with error handling
            try:
                form1_content = json.loads(form1.content)
                form2_content = json.loads(form2.content)
                result = json.loads(comparison.result)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                return jsonify({"error": f"Error parsing comparison data: {str(e)}"}), 500

            # Render the comparison template
            return render_template(
                'comparison_result.html',
                result=result,
                form1=form1_content,
                form2=form2_content,
                user1={'username': user1.username},
                user2={'username': user2.username}
            )

        except Exception as e:
            return handle_api_error(e)


# -------------------------
# Dashboard
# -------------------------
@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """User dashboard page."""
    logger.debug(f"Loading dashboard for user {current_user.username}")

    # Safety check for current_user
    if not current_user or not hasattr(current_user, 'id'):
        logger.error("Error: current_user is None or missing id attribute")
        return redirect('/login')

    with Session() as session:
        try:
            # Get current user forms
            user_forms = session.query(CompletedForm).filter_by(user_id=current_user.id).all()

            # Get all users for comparison selection
            all_users = session.query(User).all()

            # Get recent comparisons involving the current user
            user_form_ids = [form.id for form in user_forms]
            recent_comparisons = []

            if user_form_ids:
                comparisons = session.query(Comparison).filter(
                    (Comparison.form1_id.in_(user_form_ids)) |
                    (Comparison.form2_id.in_(user_form_ids))
                ).order_by(Comparison.id.desc()).limit(5).all()

                for comp in comparisons:
                    try:
                        form1 = session.query(CompletedForm).get(comp.form1_id)
                        form2 = session.query(CompletedForm).get(comp.form2_id)

                        # Skip if forms are missing
                        if not form1 or not form2:
                            logger.warning(f"Missing forms for comparison {comp.id}")
                            continue

                        user1 = session.query(User).get(form1.user_id)
                        user2 = session.query(User).get(form2.user_id)

                        # Skip if users are missing
                        if not user1 or not user2:
                            logger.warning(f"Missing users for comparison {comp.id}")
                            continue

                        recent_comparisons.append({
                            "id": comp.id,
                            "user1": user1.username,
                            "user2": user2.username
                        })
                    except Exception as inner_e:
                        logger.error(f"Error processing comparison {comp.id}: {str(inner_e)}")

            return render_template(
                'dashboard.html',
                user=current_user,
                forms=user_forms,
                comparisons=recent_comparisons,
                all_users=all_users
            )

        except Exception as e:
            return handle_api_error(e)


# -------------------------
# Main
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)