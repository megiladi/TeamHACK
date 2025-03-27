import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, redirect
from flask_login import login_required, current_user
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

# Initialize Flask application
template_folder = os.path.join(os.path.dirname(__file__), '..', 'forms')
app = Flask(__name__, template_folder=template_folder)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['ENV'] = os.getenv('FLASK_ENV', 'development')

# Path to form.html
form_html_path = os.path.join(os.path.dirname(__file__), '..', 'forms', 'form.html')

# Initialize the comparison engine with the form path
comparison_engine = ComparisonEngine(form_html_path)

# Initialize Authentication Manager
auth_manager = AuthManager(app)

# Initialize database tables
init_db()

# --------------------------
# Basic routes
# --------------------------

# redirect base site to form to fill out

@app.route('/', methods=['GET'])
def index():
    """
    Route for the root URL, redirects to the form.
    """
    return render_template('index.html')

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
        user, error_msg = auth_manager.register_user(username, email, password)

        if user:
            return jsonify({
                "message": "User registered successfully",
                "user_id": user.id
            }), 201
        else:
            return jsonify({"error": error_msg}), 409

    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({"error": "Server error during registration"}), 500

# Login

@app.route('/login', methods=['POST'])
def login():
    """User login route."""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        # Validate input
        if not all([username, password]):
            return jsonify({"error": "Missing username or password"}), 400

        # Attempt to log in the user
        user, error_msg = auth_manager.login(username, password)

        if user:
            return jsonify({
                "message": "Login successful",
                "user_id": user.id,
                "username": user.username
            }), 200
        else:
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

        new_user = User(username=data['username'], email=data['email'])

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
def create_completed_form():
    try:
        # Print the raw form data for debugging
        print(f"Form data received: {request.form}")

        # Convert form data to a dictionary
        data = request.form.to_dict()

        # Check if user_id is provided
        if 'user_id' not in data:
            return jsonify({"error": "Missing required field: user_id"}), 400

        # Validate and convert user_id to an integer
        try:
            user_id = int(data.get('user_id'))
        except (ValueError, TypeError):
            print(f"Invalid user_id: {data.get('user_id')}")
            return jsonify({"error": "Invalid user_id: must be a valid integer"}), 400

        # Check if user exists
        with Session() as session:
            user = session.query(User).get(user_id)
            if not user:
                return jsonify({"error": f"User with ID {user_id} not found"}), 404

        # Convert form data to a JSON string for storage
        content_json = json.dumps(data)

        # Create the new form object with validated user_id and JSON content
        new_form = CompletedForm(user_id=user_id, content=content_json)

        # Add to database with proper session handling
        with Session() as session:
            try:
                session.add(new_form)
                session.commit()
                # Return success response with the new form's ID
                return jsonify({"message": "Form submitted successfully", "id": new_form.id}), 201
            except Exception as e:
                # Handle database errors
                session.rollback()
                error_msg = str(e)
                print(f"Database error: {error_msg}")
                return jsonify({"error": f"Database error: {error_msg}"}), 500
    except Exception as e:
        # Handle general errors
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

# DELETE form

@app.route('/completed_forms/user/<string:username>/<int:form_id>', methods=['DELETE'])
def delete_user_form(username, form_id):
    """
    Delete a completed form by username and form ID.

    This ensures the form belongs to the specified user before deletion.

    Path parameters:
    - username: string - The username of the form owner
    - form_id: int - The ID of the form to delete
    """
    if not username or not form_id:
        return jsonify({"error": "Both username and form ID are required"}), 400

    with Session() as session:
        try:
            # First, find the user
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return jsonify({"error": f"User '{username}' not found"}), 404

            # Then find the form and verify it belongs to the user
            form = session.query(CompletedForm).get(form_id)
            if not form:
                return jsonify({"error": f"Form with ID {form_id} not found"}), 404

            # Check if the form belongs to the user
            if form.user_id != user.id:
                return jsonify({"error": "This form does not belong to the specified user"}), 403

            # Delete the form
            session.delete(form)
            session.commit()
            return jsonify({"message": f"Form with ID {form_id} deleted successfully for user '{username}'"}), 200
        except Exception as e:
            session.rollback()
            error_msg = str(e)
            print(f"Database error: {error_msg}")
            return jsonify({"error": f"Server error: {error_msg}"}), 500

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
                    form1 = session.query(CompletedForm).get(comp.form1_id)
                    form2 = session.query(CompletedForm).get(comp.form2_id)
                    user1 = session.query(User).get(form1.user_id)
                    user2 = session.query(User).get(form2.user_id)

                    recent_comparisons.append({
                        "id": comp.id,
                        "user1": user1.username,
                        "user2": user2.username
                    })

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
            comparison = session.query(Comparison).get(comparison_id)
            if not comparison:
                return jsonify({"error": f"Comparison with ID {comparison_id} not found"}), 404

            form1 = session.query(CompletedForm).get(comparison.form1_id)
            form2 = session.query(CompletedForm).get(comparison.form2_id)

            user1 = session.query(User).get(form1.user_id)
            user2 = session.query(User).get(form2.user_id)

            # Parse JSON strings
            form1_content = json.loads(form1.content)
            form2_content = json.loads(form2.content)
            result = json.loads(comparison.result)

            return render_template(
                'comparison_result.html',
                result=result,
                form1=form1_content,
                form2=form2_content,
                user1={'username': user1.username},
                user2={'username': user2.username}
            )

        except Exception as e:
            # Log the error
            print(f"Error in view_comparison_page: {str(e)}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500


# --------------------------
# Main
# --------------------------

if __name__ == '__main__':
    app.run(debug=True)
