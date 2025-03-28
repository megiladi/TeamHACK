import logging
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, redirect
from flask_login import login_required, current_user, login_user
import json

# Load environment variables
load_dotenv()

from src.models.user import User
from src.models.completed_form import CompletedForm
from src.models.comparison import Comparison
from src.db.db_setup import init_db
from src.db.db_setup import Session
from src.comparisons.comparison_engine import ComparisonEngine
from src.auth.auth_manager import AuthManager

# Configure logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'teamhack.log')),
        logging.StreamHandler()  # Also output to console
    ]
)
logger = logging.getLogger(__name__)

# Add a startup message
logger.info("Starting TeamHACK application")

# Initialize Flask application
template_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'webpages'))
app = Flask(__name__, template_folder=template_folder)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['ENV'] = os.getenv('FLASK_ENV', 'development')
app.jinja_env.autoescape = True

# Path to form.html
form_html_path = os.path.join(os.path.dirname(__file__), '..', 'webpages', 'form.html')

# Initialize the comparison engine with the form path
comparison_engine = ComparisonEngine(form_html_path)

# Initialize Authentication Manager
auth_manager = AuthManager(app)

# Initialize database tables
init_db()
print("Initializing database tables...")
init_db()
print("Database tables initialized!")

# --------------------------
# Basic routes
# --------------------------

# redirect base site to form to fill out

@app.route('/', methods=['GET'])
def index():
    """
    Route for the root URL, redirects appropriately based on authentication.
    """
    if current_user.is_authenticated:
        # Redirect authenticated users to dashboard instead
        return redirect('/dashboard')
    else:
        # Only redirect non-authenticated users to login
        return redirect('/login')

# --------------------------
# Authentication routes
# --------------------------

# Register

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
        print(f"Route exception: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# Login

@app.route('/login', methods=['POST'])
def login():
    """User login route."""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        print(f"Login attempt for username: {username}")

        # Validate input
        if not all([username, password]):
            return jsonify({"error": "Missing username or password"}), 400

        # Attempt to log in the user
        user, error_msg = auth_manager.login(username, password)

        if user:
            print(f"Login successful for {username}, user_id={user.id}")
            print(f"After login: current_user={current_user}, authenticated={current_user.is_authenticated}")
            return jsonify({
                "message": "Login successful",
                "user_id": user.id,
                "username": user.username
            }), 200
        else:
            print(f"Login failed for {username}: {error_msg}")
            return jsonify({"error": error_msg}), 401

    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({"error": "Server error during login"}), 500

# Logout

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    User logout route.
    """
    try:
        auth_manager.logout()
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return jsonify({"error": "Server error during logout"}), 500

# Diagnostic route

@app.route('/debug_login')
def debug_login():  # Changed from test_login to debug_login
    """Diagnostic route to check login functionality."""
    try:
        with Session() as session:
            # Get first user
            user = session.query(User).first()
            if user:
                login_user(user)  # We'll import this
                print(f"Debug login: Logged in as {user.username}")
                return jsonify({
                    "status": "success",
                    "message": f"Logged in as {user.username}",
                    "authenticated": current_user.is_authenticated,
                    "user_id": current_user.id
                })
            else:
                print("Debug login: No users found")
                return jsonify({"status": "error", "message": "No users found in database"})
    except Exception as e:
        print(f"Debug login error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

# --------------------------
# User routes
# --------------------------

# POST user

@app.route('/users', methods=['POST'])
def create_user():
    try:
        data = request.json
        print(f"Received data: {data}")

        # Check if required fields are present
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
            password=temp_password  # Add properly hashed password
        )

        with Session() as session:
            try:
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
                session.rollback()
                error_message = str(e)
                print(f"Database error: {error_message}")
                return jsonify({"error": f"Database error: {error_message}"}), 500
    except Exception as e:
        error_message = str(e)
        print(f"General error: {error_message}")
        return jsonify({"error": f"Server error: {error_message}"}), 500

# GET user

@app.route('/users', methods=['GET'])
def get_users():
    with Session() as session:
        try:
            users = session.query(User).all()
            user_list = [{"id": u.id, "username": u.username, "email": u.email} for u in users]
            return jsonify(user_list), 200
        except Exception as e:
            error_msg = str(e)
            print(f"Database error: {error_msg}")
            return jsonify({"error": f"Server error: {error_msg}"}), 500

# GET current user

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
        print(f"Error fetching current user: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# GET user by username

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
            return jsonify({"error": f"Server error: {str(e)}"}), 500

# --------------------------
# Form routes
# --------------------------

# GET form to fill

@app.route('/fill_form', methods=['GET'])
def fill_form():
    try:
        return render_template('form.html')
    except Exception as e:
        error_msg = str(e)
        print(f"Template error: {error_msg}")
        return jsonify({"error": f"Server error: {error_msg}"}), 500

# POST form

@app.route('/completed_forms', methods=['POST'])
@login_required
def create_completed_form():
    try:
        # Convert form data to a dictionary
        data = request.form.to_dict()

        # Use the current logged-in user instead of the form field
        user_id = current_user.id

        # Check if user exists (shouldn't be necessary with @login_required)
        with Session() as session:
            user = session.query(User).get(user_id)
            if not user:
                return jsonify({"error": f"User with ID {user_id} not found"}), 404

        # Convert form data to a JSON string for storage
        content_json = json.dumps(data)

        # Create the new form object with the current user's ID
        new_form = CompletedForm(user_id=user_id, content=content_json)

        # Add to database
        with Session() as session:
            try:
                session.add(new_form)
                session.commit()
                return jsonify({"message": "Form submitted successfully", "id": new_form.id}), 201
            except Exception as e:
                session.rollback()
                error_msg = str(e)
                print(f"Database error: {error_msg}")
                return jsonify({"error": f"Database error: {error_msg}"}), 500
    except Exception as e:
        error_msg = str(e)
        print(f"General error: {error_msg}")
        return jsonify({"error": f"Server error: {error_msg}"}), 500

# GET completed forms

@app.route('/completed_forms', methods=['GET'])
def get_completed_forms():
    with Session() as session:
        try:
            forms = session.query(CompletedForm).all()
            form_list = [{"id": f.id, "user_id": f.user_id, "content": f.content} for f in forms]
            return jsonify(form_list), 200
        except Exception as e:
            error_msg = str(e)
            print(f"Database error: {error_msg}")
            return jsonify({"error": f"Server error: {error_msg}"}), 500

# GET user forms

@app.route('/api/user_forms', methods=['GET'])
@login_required  # This ensures only logged-in users can access forms
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
            print(f"Error fetching user forms: {str(e)}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500

# GET form to view

@app.route('/view_form/<int:form_id>', methods=['GET'])
@login_required
def view_form(form_id):
    """Route to view a specific form."""
    with Session() as session:
        try:
            # Get the form
            form = session.query(CompletedForm).get(form_id)

            if not form:
                return jsonify({"error": f"Form with ID {form_id} not found"}), 404

            # Make sure the current user owns this form
            if form.user_id != current_user.id:
                return jsonify({"error": "You don't have permission to view this form"}), 403

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
                # Create a template called view_form.html to render the form data
                return render_template(
                    'view_form.html',
                    form_id=form.id,
                    username=user.username,
                    form_content=form_content
                )

        except Exception as e:
            print(f"Error viewing form: {str(e)}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500

# GET completed form by username

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
            return jsonify({"error": f"Server error: {str(e)}"}), 500

# GET edit form

@app.route('/edit_form/<int:form_id>', methods=['GET'])
@login_required
def edit_form(form_id):
    """Route to edit a specific form."""
    with Session() as session:
        try:
            # Get the form
            form = session.query(CompletedForm).get(form_id)

            if not form:
                return jsonify({"error": f"Form with ID {form_id} not found"}), 404

            # Make sure the current user owns this form
            if form.user_id != current_user.id:
                return jsonify({"error": "You don't have permission to edit this form"}), 403

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
            print(f"Error editing form: {str(e)}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500


# PUT/POST update form

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
            # Find the form
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

            # Update the form content
            form.content = content_json

            # Commit the changes
            session.commit()
            logger.info(f"Form {form_id} successfully updated by user {current_user.username}")

            return jsonify({"message": f"Form updated successfully"}), 200

    except Exception as e:
        logger.error(f"Error updating form {form_id}: {str(e)}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# DELETE form

@app.route('/completed_forms/user/<string:username>/<int:form_id>', methods=['DELETE'])
def delete_user_form(username, form_id):
    # Add proper error handling and debugging
    print(f"Attempting to delete form {form_id} for user {username}")

    with Session() as session:
        try:
            # First, find the user
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return jsonify({"error": f"User '{username}' not found"}), 404

            # Log the user ID for debugging
            print(f"Found user with ID: {user.id}")

            # Then find the form and verify it belongs to the user
            form = session.query(CompletedForm).get(form_id)
            if not form:
                return jsonify({"error": f"Form with ID {form_id} not found"}), 404

            # Log form details
            print(f"Found form with ID: {form_id}, belonging to user ID: {form.user_id}")

            # Check if the form belongs to the user
            if form.user_id != user.id:
                return jsonify({"error": "This form does not belong to the specified user"}), 403

            # Delete the form
            session.delete(form)
            session.commit()
            print(f"Form {form_id} deleted successfully")

            return jsonify({"message": f"Form with ID {form_id} deleted successfully for user '{username}'"}), 200

        except Exception as e:
            session.rollback()
            error_msg = str(e)
            print(f"Error deleting form: {error_msg}")
            return jsonify({"error": f"Server error: {error_msg}"}), 500

# delete form API route

@app.route('/api/forms/<int:form_id>', methods=['DELETE'])
@login_required
def delete_form_api(form_id):
    """API route to delete a form belonging to the current user."""
    logger.debug(f"API request to delete form {form_id} by user {current_user.username}")

    with Session() as session:
        try:
            # Find the form
            form = session.query(CompletedForm).get(form_id)
            if not form:
                logger.warning(f"Form with ID {form_id} not found")
                return jsonify({"error": f"Form with ID {form_id} not found"}), 404

            # Check if the form belongs to the current user
            if form.user_id != current_user.id:
                logger.warning(
                    f"User {current_user.username} attempted to delete form {form_id} belonging to user {form.user_id}")
                return jsonify({"error": "You don't have permission to delete this form"}), 403

            # Delete the form
            session.delete(form)
            session.commit()
            logger.info(f"Form {form_id} successfully deleted by user {current_user.username}")

            return jsonify({"message": f"Form deleted successfully"}), 200

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting form {form_id}: {str(e)}", exc_info=True)
            return jsonify({"error": f"Server error: {str(e)}"}), 500

# Debug form deletion / other

@app.route('/debug/forms', methods=['GET'])
def debug_forms():
    with Session() as session:
        forms = session.query(CompletedForm).all()
        form_list = []
        for form in forms:
            try:
                user = session.query(User).get(form.user_id)
                username = user.username if user else "Unknown"
                form_list.append({
                    "id": form.id,
                    "user_id": form.user_id,
                    "username": username
                })
            except Exception as e:
                form_list.append({
                    "id": form.id,
                    "user_id": form.user_id,
                    "error": str(e)
                })
        return jsonify({"forms": form_list})

# --------------------------
# Comparison routes
# --------------------------

# POST comparison

@app.route('/comparisons', methods=['POST'])
def create_comparison():
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
            try:
                session.add(new_comparison)
                session.commit()
                return jsonify({"message": "Comparison created", "id": new_comparison.id}), 201
            except Exception as e:
                session.rollback()
                return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# POST comparison by user IDs

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
        return jsonify({"error": str(e)}), 500

# POST comparison by usernames

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
        return jsonify({"error": str(e)}), 500

# GET comparison

@app.route('/comparisons', methods=['GET'])
def get_comparisons():
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
            error_msg = str(e)
            print(f"Database error: {error_msg}")
            return jsonify({"error": f"Server error: {error_msg}"}), 500

# GET comparison by user IDs

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
            return jsonify({"error": f"Server error: {str(e)}"}), 500

# GET comparison by usernames

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
            return jsonify({"error": f"Server error: {str(e)}"}), 500

# GET user comparison API

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
                    form1 = session.get(CompletedForm, comp.form1_id)  # Updated method
                    form2 = session.get(CompletedForm, comp.form2_id)  # Updated method

                    if not form1 or not form2:
                        continue

                    user1 = session.get(User, form1.user_id)  # Updated method
                    user2 = session.get(User, form2.user_id)  # Updated method

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
            logger.error(f"Error fetching user comparisons: {str(e)}", exc_info=True)
            return jsonify({"error": f"Server error: {str(e)}"}), 500

# --------------------------
# Webpage routes
# --------------------------

# GET login page

@app.route('/login', methods=['GET'])
def login_page():
    """Render the login page."""
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('login.html')

# GET registration page

@app.route('/register', methods=['GET'])
def register_page():
    """Render the registration page."""
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('register.html')

# GET profile page

@app.route('/profile', methods=['GET'])
@login_required
def profile():
    """
    User profile page - example of a protected route that requires login.
    This is just a simple example for testing authentication.
    """
    return jsonify({
        "message": "You are logged in!",
        "user_id": current_user.id,
        "username": current_user.username
    }), 200

# GET dashboard

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    # Add debugging to check current_user
    print(f"Dashboard: current_user is {current_user}, authenticated={current_user.is_authenticated}")

    # Safety check for current_user
    if not current_user or not hasattr(current_user, 'id'):
        print("Error: current_user is None or missing id attribute")
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

                        # Add NULL checks
                        if not form1 or not form2:
                            print(f"Warning: Missing forms for comparison {comp.id}")
                            continue

                        user1 = session.query(User).get(form1.user_id)
                        user2 = session.query(User).get(form2.user_id)

                        # Add NULL checks
                        if not user1 or not user2:
                            print(f"Warning: Missing users for comparison {comp.id}")
                            continue

                        recent_comparisons.append({
                            "id": comp.id,
                            "user1": user1.username,
                            "user2": user2.username
                        })
                    except Exception as inner_e:
                        print(f"Error processing comparison {comp.id}: {str(inner_e)}")

            return render_template(
                'dashboard.html',
                user=current_user,
                forms=user_forms,
                comparisons=recent_comparisons,
                all_users=all_users
            )

        except Exception as e:
            print(f"Dashboard error: {str(e)}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500

# GET comparison visualization

@app.route('/comparisons/<int:comparison_id>/view', methods=['GET'])
def view_comparison_page(comparison_id):
    with Session() as session:
        try:
            # Add debugging statements
            print(f"Fetching comparison with ID: {comparison_id}")

            comparison = session.query(Comparison).get(comparison_id)
            if not comparison:
                return jsonify({"error": f"Comparison with ID {comparison_id} not found"}), 404

            print(f"Found comparison between forms: {comparison.form1_id} and {comparison.form2_id}")

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
                print(f"JSON parsing error: {e}")
                return jsonify({"error": f"Error parsing comparison data: {str(e)}"}), 500

            # Verify template exists
            import os
            template_path = os.path.join(app.template_folder, 'comparison_result.html')
            if not os.path.exists(template_path):
                print(f"Template not found: {template_path}")
                return jsonify({"error": "Comparison template not found"}), 500

            print("Rendering comparison template...")

            # Add more informative error handling for template rendering
            try:
                return render_template(
                    'comparison_result.html',
                    result=result,
                    form1=form1_content,
                    form2=form2_content,
                    user1={'username': user1.username},
                    user2={'username': user2.username}
                )
            except Exception as e:
                print(f"Template rendering error: {str(e)}")
                return jsonify({"error": f"Template rendering error: {str(e)}"}), 500

        except Exception as e:
            # Log the error
            print(f"Error in view_comparison_page: {str(e)}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500

# --------------------------
# Main
# --------------------------

if __name__ == '__main__':
    app.run(debug=True)
