from flask import Flask, request, jsonify
from src.models.user import User
from src.models.completed_form import CompletedForm
from src.models.comparison import Comparison
from src.db.db_setup import Session

# Initialize Flask application
app = Flask(__name__)


# User routes

# POST user

@app.route('/users', methods=['POST'])
def create_user():
    """
    Create a new user.

    Expects JSON payload with:
    - username: string
    - email: string

    Returns:
    - JSON with user ID and success message
    - HTTP 201 on success, 400 on error
    """
    data = request.json
    new_user = User(username=data['username'], email=data['email'])

    with Session() as session:
        try:
            session.add(new_user)
            session.commit()
            return jsonify({"message": "User created", "id": new_user.id}), 201
        except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)}), 400

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


# CompletedForm routes

# POST form

@app.route('/completed_forms', methods=['POST'])
def create_completed_form():
    """
    Create a new completed form.

    Expects JSON payload with:
    - user_id: int
    - content: string (JSON format)

    Returns:
    - JSON with form ID and success message
    - HTTP 201 on success, 400 on error
    """
    data = request.json
    new_form = CompletedForm(user_id=data['user_id'], content=data['content'])

    with Session() as session:
        try:
            session.add(new_form)
            session.commit()
            return jsonify({"message": "Form created", "id": new_form.id}), 201
        except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)}), 400

# GET form

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


# Comparison routes

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


if __name__ == '__main__':
    app.run(debug=True)
