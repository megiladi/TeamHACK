import os
import json
import unittest
from flask import Flask
from src.api.app import app
from src.db.db_setup import init_db, engine, Base, Session
from src.models.user import User
from src.models.completed_form import CompletedForm
from src.models.comparison import Comparison

# Set testing environment
os.environ['TESTING'] = 'True'


class TestAPIIntegration(unittest.TestCase):
    """Integration tests for API endpoints and workflows."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment once for all tests."""
        # Ensure test mode
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

        # Set up database
        Base.metadata.create_all(engine)

        # Add test client
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        Base.metadata.drop_all(engine)

    def setUp(self):
        """Set up clean data for each test."""
        # Start with a clean session
        self.session = Session()

        # Clear existing data
        self.session.query(Comparison).delete()
        self.session.query(CompletedForm).delete()
        self.session.query(User).delete()
        self.session.commit()

    def tearDown(self):
        """Clean up after each test."""
        self.session.close()

    def test_register_login_workflow(self):
        """Test full user registration and login workflow."""
        # 1. Register a new user
        register_response = self.client.post('/register', json={
            'username': 'integration_user',
            'email': 'integration@example.com',
            'password': 'SecurePassword123!'
        })

        self.assertEqual(register_response.status_code, 201)
        register_data = json.loads(register_response.data)
        self.assertTrue('user_id' in register_data)

        # 2. Login with credentials
        login_response = self.client.post('/login', json={
            'username': 'integration_user',
            'password': 'SecurePassword123!'
        })

        self.assertEqual(login_response.status_code, 200)
        login_data = json.loads(login_response.data)
        self.assertTrue('user_id' in login_data)

        # Store cookies for authenticated requests
        auth_cookies = login_response.headers.getlist('Set-Cookie')

        # 3. Access protected endpoint (current user)
        current_user_response = self.client.get('/api/current_user', headers={
            'Cookie': '; '.join(auth_cookies)
        })

        self.assertEqual(current_user_response.status_code, 200)
        user_data = json.loads(current_user_response.data)
        self.assertEqual(user_data['username'], 'integration_user')

        # 4. Logout
        logout_response = self.client.post('/logout', headers={
            'Cookie': '; '.join(auth_cookies)
        })

        self.assertEqual(logout_response.status_code, 200)

        # 5. Verify logout by trying to access protected endpoint
        protected_response = self.client.get('/api/current_user', headers={
            'Cookie': '; '.join(auth_cookies)
        })

        # Should be redirected to login
        self.assertNotEqual(protected_response.status_code, 200)

    def test_form_submission_workflow(self):
        """Test complete form submission and retrieval workflow."""
        # 1. Register and login a test user
        self.client.post('/register', json={
            'username': 'form_workflow_user',
            'email': 'form_workflow@example.com',
            'password': 'FormPassword123!'
        })

        login_response = self.client.post('/login', json={
            'username': 'form_workflow_user',
            'password': 'FormPassword123!'
        })

        auth_cookies = login_response.headers.getlist('Set-Cookie')

        # 2. Submit a completed form
        form_data = {
            'timing_preference': '2',
            'working_hours': '3',
            'professional_goals': 'Become a tech lead',
            'ocean_openness': 'high'
        }

        submit_response = self.client.post('/completed_forms',
                                           data=form_data,
                                           headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(submit_response.status_code, 201)
        submit_data = json.loads(submit_response.data)
        form_id = submit_data['id']

        # 3. Retrieve the user's forms
        forms_response = self.client.get('/api/user_forms',
                                         headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(forms_response.status_code, 200)
        forms_data = json.loads(forms_response.data)
        self.assertTrue(len(forms_data) > 0)

        # Verify form data is correct
        found_form = False
        for form in forms_data:
            if form['id'] == form_id:
                found_form = True
                self.assertEqual(form['content']['timing_preference'], '2')
                self.assertEqual(form['content']['working_hours'], '3')
                self.assertEqual(form['content']['professional_goals'], 'Become a tech lead')

        self.assertTrue(found_form, "Submitted form not found in user's forms")

        # 4. View specific form
        view_response = self.client.get(f'/view_form/{form_id}',
                                        headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(view_response.status_code, 200)

        # 5. Edit the form
        edit_data = {
            'timing_preference': '1',  # Changed from 2 to 1
            'working_hours': '3',
            'professional_goals': 'Become a senior developer',  # Changed text
            'ocean_openness': 'high'
        }

        edit_response = self.client.post(f'/api/forms/{form_id}',
                                         data=edit_data,
                                         headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(edit_response.status_code, 200)

        # 6. Verify changes
        forms_response = self.client.get('/api/user_forms',
                                         headers={'Cookie': '; '.join(auth_cookies)})
        forms_data = json.loads(forms_response.data)

        for form in forms_data:
            if form['id'] == form_id:
                self.assertEqual(form['content']['timing_preference'], '1')
                self.assertEqual(form['content']['professional_goals'], 'Become a senior developer')

        # 7. Delete the form
        delete_response = self.client.delete(f'/api/forms/{form_id}',
                                             headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(delete_response.status_code, 200)

        # 8. Verify deletion
        forms_response = self.client.get('/api/user_forms',
                                         headers={'Cookie': '; '.join(auth_cookies)})
        forms_data = json.loads(forms_response.data)

        form_ids = [form['id'] for form in forms_data]
        self.assertNotIn(form_id, form_ids, "Form was not successfully deleted")

    def test_comparison_workflow(self):
        """Test the complete comparison workflow."""
        # 1. Create two users
        self.client.post('/register', json={
            'username': 'user_one',
            'email': 'user_one@example.com',
            'password': 'UserOne123!'
        })

        self.client.post('/register', json={
            'username': 'user_two',
            'email': 'user_two@example.com',
            'password': 'UserTwo123!'
        })

        # 2. Login as first user and submit form
        login1_response = self.client.post('/login', json={
            'username': 'user_one',
            'password': 'UserOne123!'
        })

        auth_cookies1 = login1_response.headers.getlist('Set-Cookie')

        form1_data = {
            'timing_preference': '1',  # Early bird
            'working_hours': '1',  # Set hours
            'professional_goals': 'Become a manager',
            'ocean_openness': 'high',
            'rank_opposing': '4',
            'rank_supporting': '1'
        }

        submit1_response = self.client.post('/completed_forms',
                                            data=form1_data,
                                            headers={'Cookie': '; '.join(auth_cookies1)})

        # 3. Login as second user and submit different form
        login2_response = self.client.post('/login', json={
            'username': 'user_two',
            'password': 'UserTwo123!'
        })

        auth_cookies2 = login2_response.headers.getlist('Set-Cookie')

        form2_data = {
            'timing_preference': '3',  # Night owl (conflict)
            'working_hours': '3',  # Flexible hours (conflict)
            'professional_goals': 'Become a senior developer',
            'ocean_openness': 'medium',
            'rank_opposing': '1',  # Conflict in ranking
            'rank_supporting': '3'  # Conflict in ranking
        }

        submit2_response = self.client.post('/completed_forms',
                                            data=form2_data,
                                            headers={'Cookie': '; '.join(auth_cookies2)})

        # 4. Create comparison between the users
        compare_response = self.client.post('/compare_users/usernames',
                                            json={
                                                'username1': 'user_one',
                                                'username2': 'user_two'
                                            },
                                            headers={'Cookie': '; '.join(auth_cookies1)})

        self.assertEqual(compare_response.status_code, 201)
        compare_data = json.loads(compare_response.data)
        comparison_id = compare_data['id']

        # 5. Check that comparison has identified conflicts
        self.assertTrue('result' in compare_data)
        self.assertTrue('conflict_summary' in compare_data['result'])
        self.assertTrue(compare_data['result']['conflict_summary']['total_conflicts'] > 0)

        # Verify specific conflicts are detected
        timing_conflicts = [conflict for conflict in compare_data['result']['conflict_summary']['conflict_areas']
                            if conflict['field'] == 'timing_preference']
        self.assertTrue(len(timing_conflicts) > 0, "Timing preference conflict not detected")

        # 6. View comparison details
        view_comparison_response = self.client.get(f'/comparisons/{comparison_id}/view',
                                                   headers={'Cookie': '; '.join(auth_cookies1)})

        self.assertEqual(view_comparison_response.status_code, 200)

        # 7. Check user comparisons list
        user_comparisons_response = self.client.get('/api/user_comparisons',
                                                    headers={'Cookie': '; '.join(auth_cookies1)})

        self.assertEqual(user_comparisons_response.status_code, 200)
        user_comparisons_data = json.loads(user_comparisons_response.data)
        self.assertTrue(len(user_comparisons_data) > 0)

        # Verify comparison is in the list
        found_comparison = False
        for comparison in user_comparisons_data:
            if comparison['id'] == comparison_id:
                found_comparison = True
                self.assertTrue('user1' in comparison)
                self.assertTrue('user2' in comparison)

        self.assertTrue(found_comparison, "Created comparison not found in user's comparisons")


if __name__ == '__main__':
    unittest.main()