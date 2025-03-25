from flask import Flask, request, jsonify
from src.models.user import User
from src.db.db_setup import Session

# Initialize Flask application
# This creates an instance of the Flask class, which will be our Web Server Gateway Interface (WSGI) application
app = Flask(__name__)


# Define route for creating a new user
@app.route('/users', methods=['POST'])
def create_user():
    """
    Create a new user.

    This endpoint accepts JSON data containing user information and creates a new user in the database.

    JSON payload should include:
    - username: string
    - email: string

    Returns:
    - JSON response with success message and new user ID
    - HTTP status code 201 (Created)
    """
    # Extract JSON data from the request body
    data = request.json

    # Create a new User object with the provided data
    new_user = User(username=data['username'], email=data['email'])

    # Start a new database session
    session = Session()

    try:
        # Add the new user to the session and commit changes to the database
        session.add(new_user)
        session.commit()

        # Return success message with the new user's ID
        return jsonify({"message": "User created successfully", "id": new_user.id}), 201
    except Exception as e:
        # If an error occurs, rollback the session and return an error message
        session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        # Always close the session to release database resources
        session.close()


# Define route for retrieving all users
@app.route('/users', methods=['GET'])
def get_users():
    """
    Retrieve all users.

    This endpoint returns a list of all users in the database.

    Returns:
    - JSON array of user objects, each containing id, username, and email
    - HTTP status code 200 (OK)
    """
    # Start a new database session
    session = Session()

    try:
        # Query all users from the database
        users = session.query(User).all()

        # Convert users to a list of dictionaries for JSON serialization
        user_list = [{"id": user.id, "username": user.username, "email": user.email} for user in users]

        # Return the list of users as JSON
        return jsonify(user_list), 200
    except Exception as e:
        # If an error occurs, return an error message
        return jsonify({"error": str(e)}), 500
    finally:
        # Always close the session to release database resources
        session.close()


# Run the Flask application if this file is executed directly
if __name__ == '__main__':
    app.run(debug=True)
