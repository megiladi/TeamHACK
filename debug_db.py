import json
from src.db.db_setup import Session
from src.models.user import User
from src.models.completed_form import CompletedForm


def check_database():
    with Session() as session:
        # List all users
        print("\n== USERS ==")
        users = session.query(User).all()
        for user in users:
            print(f"ID: {user.id}, Username: {user.username}")

        # List all forms
        print("\n== FORMS ==")
        forms = session.query(CompletedForm).all()
        for form in forms:
            print(f"Form ID: {form.id}, User ID: {form.user_id}")

            # Try to parse the content
            try:
                content = json.loads(form.content)
                # Print first few fields
                print(f"  Fields: {list(content.keys())[:5]}...")
            except:
                print(f"  Content could not be parsed as JSON")

        # Check if any forms exist
        if not forms:
            print("No forms found in the database!")


if __name__ == "__main__":
    check_database()