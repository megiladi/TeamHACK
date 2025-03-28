import os
import unittest
from src.db.db_setup import init_db, engine, Base, Session
from src.models.user import User
from src.models.completed_form import CompletedForm
from src.models.comparison import Comparison
from flask_bcrypt import Bcrypt

# Set testing environment
os.environ['TESTING'] = 'True'


class TestModels(unittest.TestCase):
    """Test cases for database models."""

    @classmethod
    def setUpClass(cls):
        """Set up the test database once for all tests."""
        # Make sure tables exist
        Base.metadata.create_all(engine)

        # Create a Bcrypt instance for password hashing
        cls.bcrypt = Bcrypt()

    @classmethod
    def tearDownClass(cls):
        """Clean up the test database after all tests."""
        Base.metadata.drop_all(engine)

    def setUp(self):
        """Set up clean data for each test."""
        # Start with a clean session
        self.session = Session()

        # Clear existing data for clean tests
        self.session.query(Comparison).delete()
        self.session.query(CompletedForm).delete()
        self.session.query(User).delete()
        self.session.commit()

    def tearDown(self):
        """Clean up after each test."""
        self.session.close()

    def test_user_create(self):
        """Test creating a user record."""
        # Create a test user
        hashed_password = self.bcrypt.generate_password_hash("test_password").decode('utf-8')
        test_user = User(
            username="test_user",
            email="test@example.com",
            password=hashed_password
        )

        # Add to session and commit
        self.session.add(test_user)
        self.session.commit()

        # Query to verify
        saved_user = self.session.query(User).filter_by(username="test_user").first()

        # Assert user was created correctly
        self.assertIsNotNone(saved_user)
        self.assertEqual(saved_user.username, "test_user")
        self.assertEqual(saved_user.email, "test@example.com")

        # Test password verification
        self.assertTrue(self.bcrypt.check_password_hash(saved_user.password, "test_password"))
        self.assertFalse(self.bcrypt.check_password_hash(saved_user.password, "wrong_password"))

        # Test UserMixin methods
        self.assertTrue(saved_user.is_authenticated())
        self.assertTrue(saved_user.is_active())
        self.assertFalse(saved_user.is_anonymous())
        self.assertEqual(saved_user.get_id(), str(saved_user.id))

    def test_completed_form_create(self):
        """Test creating a completed form record."""
        # First create a user
        hashed_password = self.bcrypt.generate_password_hash("test_password").decode('utf-8')
        test_user = User(
            username="form_test_user",
            email="form_test@example.com",
            password=hashed_password
        )
        self.session.add(test_user)
        self.session.commit()

        # Now create a form
        test_form = CompletedForm(
            user_id=test_user.id,
            content='{"question1": "Answer 1", "question2": "Answer 2"}'
        )
        self.session.add(test_form)
        self.session.commit()

        # Query to verify
        saved_form = self.session.query(CompletedForm).filter_by(user_id=test_user.id).first()

        # Assert form was created correctly
        self.assertIsNotNone(saved_form)
        self.assertEqual(saved_form.user_id, test_user.id)
        self.assertEqual(saved_form.content, '{"question1": "Answer 1", "question2": "Answer 2"}')

        # Test relationship (back-references)
        self.assertEqual(saved_form.user.username, "form_test_user")

    def test_comparison_create(self):
        """Test creating a comparison record."""
        # Create two users
        hashed_password = self.bcrypt.generate_password_hash("test_password").decode('utf-8')
        user1 = User(username="user1", email="user1@example.com", password=hashed_password)
        user2 = User(username="user2", email="user2@example.com", password=hashed_password)
        self.session.add_all([user1, user2])
        self.session.commit()

        # Create forms for each user
        form1 = CompletedForm(
            user_id=user1.id,
            content='{"question1": "User 1 Answer", "question2": "Same answer"}'
        )
        form2 = CompletedForm(
            user_id=user2.id,
            content='{"question1": "User 2 Answer", "question2": "Same answer"}'
        )
        self.session.add_all([form1, form2])
        self.session.commit()

        # Create a comparison
        comparison = Comparison(
            form1_id=form1.id,
            form2_id=form2.id,
            result='{"conflicts": ["question1"], "aligned": ["question2"]}'
        )
        self.session.add(comparison)
        self.session.commit()

        # Query to verify
        saved_comparison = self.session.query(Comparison).filter_by(form1_id=form1.id, form2_id=form2.id).first()

        # Assert comparison was created correctly
        self.assertIsNotNone(saved_comparison)
        self.assertEqual(saved_comparison.form1_id, form1.id)
        self.assertEqual(saved_comparison.form2_id, form2.id)
        self.assertEqual(saved_comparison.result, '{"conflicts": ["question1"], "aligned": ["question2"]}')

        # Test relationships (back-references)
        self.assertEqual(saved_comparison.form1.user_id, user1.id)
        self.assertEqual(saved_comparison.form2.user_id, user2.id)

    def test_user_form_relationship(self):
        """Test the one-to-many relationship between users and forms."""
        # Create a user
        hashed_password = self.bcrypt.generate_password_hash("test_password").decode('utf-8')
        test_user = User(
            username="relationship_test_user",
            email="relationship_test@example.com",
            password=hashed_password
        )
        self.session.add(test_user)
        self.session.commit()

        # Create multiple forms for this user
        form1 = CompletedForm(user_id=test_user.id, content='{"form": "1"}')
        form2 = CompletedForm(user_id=test_user.id, content='{"form": "2"}')
        form3 = CompletedForm(user_id=test_user.id, content='{"form": "3"}')

        self.session.add_all([form1, form2, form3])
        self.session.commit()

        # Get user with forms
        user_with_forms = self.session.query(User).filter_by(id=test_user.id).first()

        # Test the relationship
        self.assertEqual(len(user_with_forms.completed_forms), 3)
        # Check that the forms belong to the user
        for form in user_with_forms.completed_forms:
            self.assertEqual(form.user_id, test_user.id)


if __name__ == '__main__':
    unittest.main()