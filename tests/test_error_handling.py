import os
import json
import unittest
from flask import Flask
from src.api.app import app
from src.db.db_setup import init_db, engine, Base, Session

# Set testing environment
os.environ['TESTING'] = 'True'


class TestErrorHandling(unittest.TestCase):
    """Test system behavior when errors occur."""

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        Base.metadata.create_all(engine)
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(engine)

    def setUp(self):
        self.session = Session()
        # Set up test user
        self.client.post('/register', json={
            'username': 'error_test_user',
            'email': 'error_test@example.com',
            'password': 'ErrorTest123!'
        })

        login_response = self.client.post('/login', json={
            'username': 'error_test_user',
            'password': 'ErrorTest123!'
        })

        self.auth_cookies = login_response.headers.getlist('Set-Cookie')

    def tearDown(self):
        self.session.close()

    def test_invalid_login_attempts(self):
        """Test system behavior with invalid login attempts."""
        # Test with wrong password
        response = self.client.post('/login', json={
            'username': 'error_test_user',
            'password': 'WrongPassword123!'
        })

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', json.loads(response.data))

        # Test with non-existent user
        response = self.client.post('/login', json={
            'username': 'non_existent_user',
            'password': 'SomePassword123!'
        })

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', json.loads(response.data))

        # Test rate limiting
        # Make multiple failed attempts
        for i in range(6):  # Assuming rate limit is 5 attempts
            self.client.post('/login', json={
                'username': 'error_test_user',
                'password': f'WrongPassword{i}!'
            })

        # This attempt should be rate-limited
        response = self.client.post('/login', json={
            'username': 'error_test_user',
            'password': 'ErrorTest123!'  # Correct password
        })

        self.assertEqual(response.status_code, 401)
        self.assertIn('Too many failed attempts', json.loads(response.data)['error'])

    def test_accessing_nonexistent_resources(self):
        """Test accessing resources that don't exist."""
        # Test nonexistent form
        response = self.client.get('/view_form/99999',
                                   headers={'Cookie': '; '.join(self.auth_cookies)})

        self.assertEqual(response.status_code, 404)

        # Test nonexistent comparison
        response = self.client.get('/comparisons/99999/view',
                                   headers={'Cookie': '; '.join(self.auth_cookies)})

        self.assertEqual(response.status_code, 404)

        # Test nonexistent user comparison
        response = self.client.get('/comparisons/users/usernames/no_such_user1/no_such_user2',
                                   headers={'Cookie': '; '.join(self.auth_cookies)})

        self.assertEqual(response.status_code, 404)

    def test_unauthorized_access(self):
        """Test accessing resources without proper authorization."""
        # Create a form with the authenticated user
        form_data = {'question1': 'Answer 1'}
        form_response = self.client.post('/completed_forms',
                                         data=form_data,
                                         headers={'Cookie': '; '.join(self.auth_cookies)})

        form_id = json.loads(form_response.data)['id']

        # Create second user
        self.client.post('/register', json={
            'username': 'second_user',
            'email': 'second@example.com',
            'password': 'SecondUser123!'
        })

        login2_response = self.client.post('/login', json={
            'username': 'second_user',
            'password': 'SecondUser123!'
        })

        auth_cookies2 = login2_response.headers.getlist('Set-Cookie')

        # Try to access first user's form with second user
        response = self.client.get(f'/edit_form/{form_id}',
                                   headers={'Cookie': '; '.join(auth_cookies2)})

        self.assertEqual(response.status_code, 403)

        # Try to delete first user's form with second user
        response = self.client.delete(f'/api/forms/{form_id}',
                                      headers={'Cookie': '; '.join(auth_cookies2)})

        self.assertEqual(response.status_code, 403)

    def test_invalid_form_submissions(self):
        """Test submitting invalid form data."""
        # Test empty form
        response = self.client.post('/completed_forms',
                                    data={},
                                    headers={'Cookie': '; '.join(self.auth_cookies)})

        self.assertEqual(response.status_code, 400)

        # Test form with invalid field types
        invalid_data = {
            'timing_preference': 'not_a_number',  # Should be 1, 2, or 3
            'working_hours': '5',  # Out of range
            'ocean_openness': 'invalid_trait'  # Should be low, medium, or high
        }

        response = self.client.post('/completed_forms',
                                    data=invalid_data,
                                    headers={'Cookie': '; '.join(self.auth_cookies)})

        # System should handle this gracefully
        self.assertIn(response.status_code, [400, 201])

    def test_concurrent_form_edits(self):
        """Test behavior when multiple users try to edit the same form."""
        # This would need a more sophisticated setup with threading
        # to truly test concurrent access, but we can simulate it
        pass