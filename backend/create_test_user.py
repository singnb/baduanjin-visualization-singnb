# create_test_user.py
from database import engine, Base, SessionLocal
import models
from passlib.context import CryptContext
from models import User, UserRole

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_test_user():
    db = SessionLocal()
    try:
        # Check if test user already exists
        test_user = db.query(models.User).filter(models.User.email == "test@example.com").first()
        if test_user:
            print("Test user already exists!")
            return
        
        # Create hashed password
        hashed_password = pwd_context.hash("testpassword123")
        
        # Create new user - use models.UserRole.LEARNER instead of string
        new_user = User(
            email="test@example.com",
            username="testuser",
            name="Test User",
            hashed_password=hashed_password,
            role=UserRole.LEARNER,  # Use the enum directly, not string
            is_active=True,
            agreement_accepted=True
        )
        
        db.add(new_user)
        db.commit()
        print("Test user created successfully!")
    except Exception as e:
        print(f"Error creating test user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()