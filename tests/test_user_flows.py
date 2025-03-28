import os
import json
import unittest
from flask import Flask
from src.api.app import app
from src.db.db_setup import init_db, engine, Base, Session

# Set testing environment
os.environ['TESTING'] = 'True'


class TestUserFlows(unittest.TestCase):
    """Test complete user journeys through the system."""

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
        # Clear database tables as needed

    def tearDown(self):
        self.session.close()

    def test_new_user_complete_journey(self):
        """Test the journey of a brand new user through the entire system."""
        # 1. Register a new user
        register_response = self.client.post('/register', json={
            'username': 'journey_user',
            'email': 'journey@example.com',
            'password': 'JourneyPassword123!'
        })

        self.assertEqual(register_response.status_code, 201)

        # 2. Login with new account
        login_response = self.client.post('/login', json={
            'username': 'journey_user',
            'password': 'JourneyPassword123!'
        })

        self.assertEqual(login_response.status_code, 200)
        auth_cookies = login_response.headers.getlist('Set-Cookie')

        # 3. Visit dashboard (should be empty)
        dashboard_response = self.client.get('/dashboard',
                                             headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(dashboard_response.status_code, 200)

        # 4. Fill out a new form
        form_data = {
            'timing_preference': '2',
            'working_hours': '3',
            'professional_goals': 'Test journey goals',
            'ocean_openness': 'high'
            # Add more fields as needed
        }

        form_response = self.client.post('/completed_forms',
                                         data=form_data,
                                         headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(form_response.status_code, 201)
        form_id = json.loads(form_response.data)['id']

        # 5. Create another user to compare with
        self.client.post('/register', json={
            'username': 'compare_user',
            'email': 'compare@example.com',
            'password': 'ComparePassword123!'
        })

        # 6. Login as second user and create form
        login2_response = self.client.post('/login', json={
            'username': 'compare_user',
            'password': 'ComparePassword123!'
        })

        auth_cookies2 = login2_response.headers.getlist('Set-Cookie')

        form2_data = {
            'timing_preference': '1',
            'working_hours': '1',
            'professional_goals': 'Different goals',
            'ocean_openness': 'medium'
        }

        self.client.post('/completed_forms',
                         data=form2_data,
                         headers={'Cookie': '; '.join(auth_cookies2)})

        # 7. Return to first user and create comparison
        comparison_response = self.client.post('/compare_users/usernames',
                                               json={
                                                   'username1': 'journey_user',
                                                   'username2': 'compare_user'
                                               },
                                               headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(comparison_response.status_code, 201)
        comparison_id = json.loads(comparison_response.data)['id']

        # 8. View comparison
        view_comp_response = self.client.get(f'/comparisons/{comparison_id}/view',
                                             headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(view_comp_response.status_code, 200)

        # 9. Check updated dashboard
        updated_dashboard = self.client.get('/dashboard',
                                            headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(updated_dashboard.status_code, 200)
        # Verify dashboard shows form and comparison

        # 10. Logout
        logout_response = self.client.post('/logout',
                                           headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(logout_response.status_code, 200)

    def test_form_management_journey(self):
        """Test a journey focused on managing multiple forms."""
        # Similar structure but focusing on creating multiple forms,
        # editing them, deleting them, etc.
        pass

    def test_comparison_journey(self):
        """Test a journey focused on creating and analyzing comparisons."""
        # Similar structure but focusing on multiple comparisons,
        # different comparison scenarios, etc.
        pass