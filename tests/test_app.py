import os
os.environ['TESTING'] = 'True'
import pytest
from src.api.app import app
from src.db.db_setup import init_db, engine, Base


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

# Users

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

# Forms

def test_create_completed_form(client):
    # First, create a user
    user_response = client.post('/users', json={'username': 'form_user', 'email': 'form@example.com'})
    user_id = user_response.json['id']

    # Now create a form for this user
    form_data = {
        'user_id': user_id,
        'question1': 'Answer 1',
        'question2': 'Answer 2'
    }
    response = client.post('/completed_forms', data=form_data)
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


def test_delete_user_form(client):
    """Test deleting a form with username + form ID authentication"""
    # First, create a user and a form
    username = 'delete_user'
    user_response = client.post('/users', json={'username': username, 'email': 'delete@example.com'})
    user_id = user_response.json['id']

    form_data = {
        'user_id': user_id,
        'question1': 'Delete me',
    }
    form_response = client.post('/completed_forms', data=form_data)
    form_id = form_response.json['id']

    # Now delete the form using username + form ID
    response = client.delete(f'/completed_forms/user/{username}/{form_id}')
    assert response.status_code == 200
    assert 'deleted successfully' in response.json['message']

    # Verify deletion by trying to retrieve all forms for the user
    get_response = client.get(f'/forms/user/{username}')
    assert get_response.status_code in [404, 200]  # Either no forms found (404) or empty list (200)

    # Add test for unauthorized deletion (wrong username)
    # First create a second user and try to delete the first user's form
    client.post('/users', json={'username': 'another_user', 'email': 'another@example.com'})

    # Create another form for the original user
    form_data2 = {
        'user_id': user_id,
        'question1': 'Another form',
    }
    form_response2 = client.post('/completed_forms', data=form_data2)
    form_id2 = form_response2.json['id']

    # Try to delete with wrong username
    unauthorized_response = client.delete(f'/completed_forms/user/another_user/{form_id2}')
    assert unauthorized_response.status_code == 403  # Forbidden
    assert 'does not belong to' in unauthorized_response.json['error']

def test_create_completed_form_missing_user_id(client):
    """Test form submission with missing user_id."""
    form_data = {
        # No user_id provided
        'question1': 'Answer 1'
    }
    response = client.post('/completed_forms', data=form_data)
    assert response.status_code == 400
    assert 'Missing required field' in response.json['error']

def test_get_nonexistent_form(client):
    """Test retrieving a form that doesn't exist."""
    response = client.get('/forms/user/nonexistent_user')
    assert response.status_code == 404
    assert 'nonexistent_user' in response.json['error']
    assert 'not found' in response.json['error']

# Comparisons

def test_create_comparison(client):
    # First, create two forms
    user_response = client.post('/users', json={'username': 'comp_user', 'email': 'comp@example.com'})
    user_id = user_response.json['id']

    form_data1 = {'user_id': user_id, 'question1': 'Form 1'}
    form_data2 = {'user_id': user_id, 'question1': 'Form 2'}

    form1_response = client.post('/completed_forms', data=form_data1)
    form2_response = client.post('/completed_forms', data=form_data2)

    form1_id = form1_response.json['id']
    form2_id = form2_response.json['id']

    # Now create a comparison
    comparison_data = {
        'form1_id': form1_id,
        'form2_id': form2_id,
        'result': '{"similarity": 0.5}'
    }
    response = client.post('/comparisons', json=comparison_data)
    assert response.status_code == 201
    assert 'Comparison created' in response.json['message']


def test_get_comparisons(client):
    response = client.get('/comparisons')
    assert response.status_code == 200
    assert isinstance(response.json, list)
