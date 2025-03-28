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

    def test_form_deletion_and_recreation(self):
        """
        Test that users can delete forms and create new ones without issues.
        Specifically verifies:
        1. Deleting a form doesn't break subsequent form creation
        2. New forms get new IDs (not reusing deleted IDs)
        3. Comparisons correctly pull the latest form for each user
        """
        # Register and login two users
        self.client.post('/register', json={
            'username': 'form_delete_user',
            'email': 'form_delete@example.com',
            'password': 'DeleteTest123!'
        })

        self.client.post('/register', json={
            'username': 'comparison_partner',
            'email': 'partner@example.com',
            'password': 'PartnerTest123!'
        })

        login_response = self.client.post('/login', json={
            'username': 'form_delete_user',
            'password': 'DeleteTest123!'
        })

        auth_cookies = login_response.headers.getlist('Set-Cookie')

        # Create three forms for main user
        form_ids = []
        for i in range(3):
            form_data = {
                'timing_preference': str(i % 3 + 1),  # Values 1, 2, 3
                'working_hours': '3',
                'professional_goals': f'Form {i + 1} goals',
                'ocean_openness': 'high'
            }

            form_response = self.client.post('/completed_forms',
                                             data=form_data,
                                             headers={'Cookie': '; '.join(auth_cookies)})

            self.assertEqual(form_response.status_code, 201)
            form_id = json.loads(form_response.data)['id']
            form_ids.append(form_id)

        # Verify we have three sequential form IDs
        self.assertEqual(len(form_ids), 3)
        print(f"Created forms with IDs: {form_ids}")

        # Delete the middle form (index 1)
        middle_form_id = form_ids[1]
        delete_response = self.client.delete(f'/api/forms/{middle_form_id}',
                                             headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(delete_response.status_code, 200)

        # Get the user's forms and verify middle form is gone
        forms_response = self.client.get('/api/user_forms',
                                         headers={'Cookie': '; '.join(auth_cookies)})

        forms_data = json.loads(forms_response.data)
        remaining_form_ids = [form['id'] for form in forms_data]

        self.assertNotIn(middle_form_id, remaining_form_ids, "Middle form should be deleted")
        self.assertIn(form_ids[0], remaining_form_ids, "First form should still exist")
        self.assertIn(form_ids[2], remaining_form_ids, "Last form should still exist")

        # Create a new form
        new_form_data = {
            'timing_preference': '2',
            'working_hours': '2',
            'professional_goals': 'New form after deletion',
            'ocean_openness': 'medium'
        }

        new_form_response = self.client.post('/completed_forms',
                                             data=new_form_data,
                                             headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(new_form_response.status_code, 201)
        new_form_id = json.loads(new_form_response.data)['id']

        # Verify new form has a new ID (not reusing the deleted ID)
        self.assertNotEqual(new_form_id, middle_form_id,
                            "New form should not reuse deleted form's ID")

        # Verify that when we create a comparison, it uses the newest form
        # Create a form for the second user
        login2_response = self.client.post('/login', json={
            'username': 'comparison_partner',
            'password': 'PartnerTest123!'
        })

        auth_cookies2 = login2_response.headers.getlist('Set-Cookie')

        partner_form_data = {
            'timing_preference': '3',
            'working_hours': '1',
            'professional_goals': 'Partner goals',
            'ocean_openness': 'low'
        }

        self.client.post('/completed_forms',
                         data=partner_form_data,
                         headers={'Cookie': '; '.join(auth_cookies2)})

        # Create comparison
        comparison_response = self.client.post('/compare_users/usernames',
                                               json={
                                                   'username1': 'form_delete_user',
                                                   'username2': 'comparison_partner'
                                               },
                                               headers={'Cookie': '; '.join(auth_cookies)})

        self.assertEqual(comparison_response.status_code, 201)
        comparison_data = json.loads(comparison_response.data)

        # Now verify that the form used in the comparison is the new form
        # This is tricky - we need to look at the form1_id in the comparison
        # Retrieve the comparison details to check which form was used
        with Session() as session:
            from src.models.comparison import Comparison
            from src.models.completed_form import CompletedForm

            comparison = session.query(Comparison).get(comparison_data['id'])
            self.assertIsNotNone(comparison, "Comparison should exist")

            # Check which form of the main user was used
            main_user_form_id = comparison.form1_id

            # Verify it's the newest form
            self.assertEqual(main_user_form_id, new_form_id,
                             "Comparison should use the newest form of the user")