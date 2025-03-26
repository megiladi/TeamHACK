from flask import Flask, request, jsonify
import json
from src.models.user import User
from src.models.completed_form import CompletedForm
from src.models.comparison import Comparison
from src.db.db_setup import Session

# Initialize Flask application
app = Flask(__name__, template_folder='src/forms')

# --------------------------
# User routes
# --------------------------

# POST user

@app.route('/users', methods=['POST'])
def create_user():
    """
    Create a new user.
    """
    try:
        data = request.json
        print(f"Received data: {data}")

        # Check if required fields are present
        if 'username' not in data or 'email' not in data:
            return jsonify({"error": "Missing required fields: username and email"}), 400

        new_user = User(username=data['username'], email=data['email'])

        with Session() as session:
            try:
                session.add(new_user)
                session.commit()
                return jsonify({"message": "User created", "id": new_user.id}), 201
            except Exception as e:
                session.rollback()
                error_message = str(e)
                print(f"Database error: {error_message}")
                return jsonify({"error": error_message}), 400
    except Exception as e:
        error_message = str(e)
        print(f"General error: {error_message}")
        return jsonify({"error": error_message}), 400

# GET user

@app.route('/users', methods=['GET'])
def get_users():
    """
    Retrieve all users.

    Returns:
    - JSON list of all users
    - HTTP 200 on success, 500 on error
    """
    with Session() as session:
        try:
            users = session.query(User).all()
            user_list = [{"id": u.id, "username": u.username, "email": u.email} for u in users]
            return jsonify(user_list), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# --------------------------
# Form routes
# --------------------------

# GET form to fill

@app.route('/fill_form', methods=['GET'])
def fill_form():
    """
    Render the form template for users to fill out.

    Returns:
    - HTML page with the form
    """
    return render_template('form.html')

# POST form

@app.route('/completed_forms', methods=['POST'])
def create_completed_form():
    """Create a new completed form."""
    try:
        # Print the raw form data for debugging
        print(f"Form data received: {request.form}")

        # Convert form data to a dictionary
        data = request.form.to_dict()

        # Validate and convert user_id to an integer
        try:
            user_id = int(data.get('user_id'))
        except (ValueError, TypeError):
            print(f"Invalid user_id: {data.get('user_id')}")
            return jsonify({"error": "Invalid user_id"}), 400

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
                return jsonify({"error": error_msg}), 400
    except Exception as e:
        # Handle general errors
        error_msg = str(e)
        print(f"General error: {error_msg}")
        return jsonify({"error": error_msg}), 400

# GET completed forms

@app.route('/completed_forms', methods=['GET'])
def get_completed_forms():
    """
    Retrieve all completed forms.

    Returns:
    - JSON list of all completed forms
    - HTTP 200 on success, 500 on error
    """
    with Session() as session:
        try:
            forms = session.query(CompletedForm).all()
            form_list = [{"id": f.id, "user_id": f.user_id, "content": f.content} for f in forms]
            return jsonify(form_list), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# GET completed form by username

@app.route('/forms/user/<string:username>', methods=['GET'])
def get_forms_by_user(username):
    """
    Retrieve all forms submitted by a specific user.

    Path parameter:
    - username: string

    Returns:
    - JSON list of all forms tied to the user
    - HTTP 200 on success, 404 if no forms found
    """
    with Session() as session:
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            forms = session.query(CompletedForm).filter_by(user_id=user.id).all()
            if not forms:
                return jsonify({"error": "No forms found for this user"}), 404

            return jsonify([{"id": f.id, "content": f.content} for f in forms]), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# DELETE form

@app.route('/completed_forms/<int:form_id>', methods=['DELETE'])
def delete_completed_form(form_id):
    """
    Delete a completed form by ID.

    Path parameter:
    - form_id: int

    Returns:
    - JSON with success message
    - HTTP 200 on success, 404 if not found, 500 on error
    """
    with Session() as session:
        try:
            form = session.query(CompletedForm).get(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404
            session.delete(form)
            session.commit()
            return jsonify({"message": "Form deleted"}), 200
        except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)}), 500


# --------------------------
# Comparison routes
# --------------------------

# POST comparison

@app.route('/comparisons', methods=['POST'])
def create_comparison():
    """
    Create a new comparison.

    Expects JSON payload with:
    - form1_id: int
    - form2_id: int
    - result: string (JSON format)

    Returns:
    - JSON with comparison ID and success message
    - HTTP 201 on success, 400 on error
    """
    data = request.json
    new_comparison = Comparison(form1_id=data['form1_id'], form2_id=data['form2_id'], result=data['result'])

    with Session() as session:
        try:
            session.add(new_comparison)
            session.commit()
            return jsonify({"message": "Comparison created", "id": new_comparison.id}), 201
        except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)}), 400

# GET comparison

@app.route('/comparisons', methods=['GET'])
def get_comparisons():
    """
    Retrieve all comparisons.

    Returns:
    - JSON list of all comparisons
    - HTTP 200 on success, 500 on error
    """
    with Session() as session:
        try:
            comparisons = session.query(Comparison).all()
            comparison_list = [{"id": c.id, "form1_id": c.form1_id, "form2_id": c.form2_id, "result": c.result} for c in
                               comparisons]
            return jsonify(comparison_list), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# --------------------------
# Main
# --------------------------

if __name__ == '__main__':
    app.run(debug=True)
