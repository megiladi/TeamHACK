import os

os.environ['TESTING'] = 'True'
import pytest
from src.api.app import app
from src.db.db_setup import init_db, engine, Base
from src.models.user import User
from flask_login import login_user
from src.db.db_setup import Session


@pytest.fixture
def client():
    print("\n--- Setting up test database ---")
    app.config['TESTING'] = True

    # Make sure tables exist
    Base.metadata.create_all(engine)
    print("--- Tables created ---")

    with app.test_client() as client:
        yield client

    print("\n--- Tearing down test database ---")
    Base.metadata.drop_all(engine)


@pytest.fixture
def authenticated_client():
    """Create a test client with an authenticated user"""
    print("\n--- Setting up authenticated test database ---")
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'  # Ensure we have a secret key for sessions

    # Generate unique identifiers for this test run
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    test_username = f"test_user_{unique_id}"
    test_email = f"test_{unique_id}@example.com"

    print(f"Creating test user: {test_username} with email: {test_email}")

    # Make sure tables exist
    Base.metadata.create_all(engine)
    print("--- Tables created ---")

    # Create a test client
    client = app.test_client()

    # Create a test user in the database
    with app.app_context():
        with Session() as session:
            # Create a password hash
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt()
            hashed_password = bcrypt.generate_password_hash("testpassword123").decode('utf-8')

            # Create new user
            test_user = User(
                username=test_username,
                email=test_email,
                password=hashed_password
            )
            session.add(test_user)
            session.commit()

            # Store user ID for later
            user_id = test_user.id
            print(f"Created test user: {test_user.username} (ID: {user_id})")

    # Simulate user login by setting session cookie
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True

    print(f"Logged in test user: {test_username} (ID: {user_id})")

    yield client

    print("\n--- Tearing down authenticated test database ---")
    Base.metadata.drop_all(engine)


# Users - These don't require authentication

def test_create_user(client):
    payload = {'username': 'test_user', 'email': 'test@example.com'}
    print(f"Sending request with payload: {payload}")

    response = client.post('/users', json=payload)

    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data.decode('utf-8')}")

    assert response.status_code == 201
    assert 'User created' in response.json['message']


def test_get_users(client):
    response = client.get('/users')
    assert response.status_code == 200
    assert isinstance(response.json, list)


# Forms - These require authentication

def test_create_completed_form(authenticated_client):
    # No need to create a separate user, use the authenticated user

    # Create a form
    form_data = {
        'question1': 'Answer 1',
        'question2': 'Answer 2'
    }
    response = authenticated_client.post('/completed_forms', data=form_data)
    print(f"Form submission response: {response.status_code}, {response.data.decode('utf-8')}")

    assert response.status_code == 201
    assert 'Form submitted successfully' in response.json['message']


def test_get_completed_forms(client):
    response = client.get('/completed_forms')
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_get_forms_by_user(client):
    # First, create a user
    user_response = client.post('/users', json={'username': 'user_forms', 'email': 'userforms@example.com'})
    username = 'user_forms'

    # Now get forms for this user
    response = client.get(f'/forms/user/{username}')
    assert response.status_code in [200, 404]  # 404 if no forms yet, 200 if forms exist


def test_delete_user_form(authenticated_client):
    """Test deleting a form using the authenticated user"""
    # Create a form for the authenticated user
    form_data = {
        'question1': 'Delete me'
    }

    # Submit the form
    form_response = authenticated_client.post('/completed_forms', data=form_data)
    print(f"Form creation response: {form_response.status_code}, {form_response.data.decode('utf-8')}")

    # Check if form was created successfully
    assert form_response.status_code == 201
    form_id = form_response.json['id']

    # Now delete the form using the API
    delete_response = authenticated_client.delete(f'/api/forms/{form_id}')
    print(f"Form deletion response: {delete_response.status_code}, {delete_response.data.decode('utf-8')}")

    assert delete_response.status_code == 200
    assert 'deleted successfully' in delete_response.json['message']


def test_create_completed_form_invalid_data(authenticated_client):
    """Test form submission with missing required fields."""
    # Empty form data
    form_data = {}
    response = authenticated_client.post('/completed_forms', data=form_data)
    print(f"Invalid form response: {response.status_code}, {response.data.decode('utf-8')}")

    # Either expect a 400 Bad Request or at least check that it's not successful
    assert response.status_code != 201
    if response.status_code == 400:
        assert 'error' in response.json


def test_get_nonexistent_form(authenticated_client):
    """Test retrieving a form that doesn't exist."""
    # Generate a unique random username that definitely won't exist
    import uuid
    random_username = f"nonexistent_user_{uuid.uuid4().hex}"

    response = authenticated_client.get(f'/forms/user/{random_username}/latest')
    print(f"Get nonexistent form response: {response.status_code}, {response.data.decode('utf-8')}")

    assert response.status_code == 404
    response_data = response.get_json()
    assert response_data is not None
    assert 'error' in response_data


# Comparisons

def test_create_comparison(authenticated_client):
    # Create two forms for the authenticated user
    form_data1 = {'question1': 'Form 1'}
    form_data2 = {'question1': 'Form 2'}

    form1_response = authenticated_client.post('/completed_forms', data=form_data1)
    print(f"Form 1 creation response: {form1_response.status_code}, {form1_response.data.decode('utf-8')}")

    form2_response = authenticated_client.post('/completed_forms', data=form_data2)
    print(f"Form 2 creation response: {form2_response.status_code}, {form2_response.data.decode('utf-8')}")

    # Check if forms were created successfully
    assert form1_response.status_code == 201
    assert form2_response.status_code == 201

    form1_id = form1_response.json['id']
    form2_id = form2_response.json['id']

    # Create a comparison
    comparison_data = {
        'form1_id': form1_id,
        'form2_id': form2_id,
        'result': '{"similarity": 0.5}'
    }

    response = authenticated_client.post('/comparisons', json=comparison_data)
    print(f"Comparison creation response: {response.status_code}, {response.data.decode('utf-8')}")

    assert response.status_code == 201
    assert 'Comparison created' in response.json['message']


def test_get_comparisons(client):
    response = client.get('/comparisons')
    assert response.status_code == 200
    assert isinstance(response.json, list)