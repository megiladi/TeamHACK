import os
from flask import Flask, request, jsonify, render_template
import json
from src.models.user import User
from src.models.completed_form import CompletedForm
from src.models.comparison import Comparison
from src.db.db_setup import Session

# Initialize Flask application
template_folder = os.path.join(os.path.dirname(__file__), '..', 'forms')
app = Flask(__name__, template_folder=template_folder)

# --------------------------
# Basic routes
# --------------------------

# redirect base site to form to fill out

@app.route('/', methods=['GET'])
def index():
    """
    Route for the root URL, redirects to the form.
    """
    return render_template('form.html')

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

@app.route('/forms/user/<string:username>', methods=['GET'])
def get_forms_by_user(username):
    if not username:
        return jsonify({"error": "Username parameter is required"}), 400

    with Session() as session:
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return jsonify({"error": f"User '{username}' not found"}), 404

            forms = session.query(CompletedForm).filter_by(user_id=user.id).all()
            if not forms:
                return jsonify({"message": f"No forms found for user '{username}'", "forms": []}), 200

            return jsonify([{"id": f.id, "content": f.content} for f in forms]), 200
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

# --------------------------
# Main
# --------------------------

if __name__ == '__main__':
    app.run(debug=True)
