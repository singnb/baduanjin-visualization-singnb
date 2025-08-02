# type: ignore
# /tests/auth/test_auth_router.py
# Unit tests for auth/router.py core functions

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from jose import jwt
from fastapi import HTTPException
import sys
import os

# Add the auth directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'auth'))

# Import the functions we want to test
from router import (
    verify_password, 
    get_password_hash,
    create_access_token,
    create_refresh_token,
    authenticate_user,
    get_user_by_email,
    get_user_by_username,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)

class TestPasswordFunctions:
    """Test password hashing and verification"""
    
    def test_password_hashing(self):
        """Test that password hashing works correctly"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Hash should not be the same as original password
        assert hashed != password
        # Hash should always be different for same password (due to salt)
        hashed2 = get_password_hash(password)
        assert hashed != hashed2
        # But verification should work for both
        assert verify_password(password, hashed)
        assert verify_password(password, hashed2)
    
    def test_password_verification_success(self):
        """Test successful password verification"""
        password = "correct_password"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
    
    def test_password_verification_failure(self):
        """Test failed password verification"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False
    
    def test_empty_password_handling(self):
        """Test handling of empty passwords"""
        empty_password = ""
        hashed = get_password_hash(empty_password)
        assert verify_password(empty_password, hashed) is True
        assert verify_password("not_empty", hashed) is False


class TestTokenFunctions:
    """Test JWT token creation and validation"""
    
    def test_create_access_token_default_expiry(self):
        """Test access token creation with default expiry"""
        data = {"sub": "test@example.com", "user_id": 1}
        token = create_access_token(data)
        
        # Decode token to verify contents
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert payload["user_id"] == 1
        assert "exp" in payload
    
    def test_create_access_token_custom_expiry(self):
        """Test access token creation with custom expiry"""
        data = {"sub": "test@example.com", "user_id": 1}
        custom_expiry = timedelta(minutes=60)
        token = create_access_token(data, custom_expiry)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check that expiry is approximately 60 minutes from now
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_time = datetime.utcnow() + custom_expiry
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 5  # Allow 5 seconds tolerance
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"sub": "test@example.com", "user_id": 1}
        token = create_refresh_token(data)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert payload["user_id"] == 1
        
        # Check that expiry is approximately 30 days from now
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_time = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 60  # Allow 1 minute tolerance
    
    def test_token_with_invalid_data(self):
        """Test token creation with various data types"""
        # Test with None data
        token = create_access_token({})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload
        
        # Test with additional data
        data = {
            "sub": "test@example.com", 
            "user_id": 1,
            "role": "admin",
            "permissions": ["read", "write"]
        }
        token = create_access_token(data)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]


class TestDatabaseQueryFunctions:
    """Test database query functions with mocked database"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        return Mock()
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user object"""
        user = Mock()
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.hashed_password = "hashed_password_here"
        user.name = "Test User"
        user.role.value = "learner"
        return user
    
    def test_get_user_by_email_found(self, mock_db_session, mock_user):
        """Test getting user by email when user exists"""
        # Setup mock
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_user_by_email(mock_db_session, "test@example.com")
        
        assert result == mock_user
        mock_db_session.query.assert_called_once()
    
    def test_get_user_by_email_not_found(self, mock_db_session):
        """Test getting user by email when user doesn't exist"""
        # Setup mock to return None
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        result = get_user_by_email(mock_db_session, "nonexistent@example.com")
        
        assert result is None
        mock_db_session.query.assert_called_once()
    
    def test_get_user_by_username_found(self, mock_db_session, mock_user):
        """Test getting user by username when user exists"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_user_by_username(mock_db_session, "testuser")
        
        assert result == mock_user
        mock_db_session.query.assert_called_once()
    
    def test_get_user_by_username_not_found(self, mock_db_session):
        """Test getting user by username when user doesn't exist"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        result = get_user_by_username(mock_db_session, "nonexistent")
        
        assert result is None
        mock_db_session.query.assert_called_once()


class TestAuthenticateUser:
    """Test user authentication function"""
    
    @pytest.fixture
    def mock_db_session(self):
        return Mock()
    
    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.hashed_password = get_password_hash("correct_password")
        return user
    
    @patch('router.get_user_by_email')
    @patch('router.verify_password')
    def test_authenticate_user_by_email_success(self, mock_verify, mock_get_email, mock_db_session, mock_user):
        """Test successful authentication using email"""
        mock_get_email.return_value = mock_user
        mock_verify.return_value = True
        
        result = authenticate_user(mock_db_session, "test@example.com", "correct_password")
        
        assert result == mock_user
        mock_get_email.assert_called_once_with(mock_db_session, "test@example.com")
        mock_verify.assert_called_once_with("correct_password", mock_user.hashed_password)
    
    @patch('router.get_user_by_email')
    @patch('router.get_user_by_username')
    @patch('router.verify_password')
    def test_authenticate_user_by_username_success(self, mock_verify, mock_get_username, mock_get_email, mock_db_session, mock_user):
        """Test successful authentication using username when email not found"""
        mock_get_email.return_value = None  # Email not found
        mock_get_username.return_value = mock_user  # Username found
        mock_verify.return_value = True
        
        result = authenticate_user(mock_db_session, "testuser", "correct_password")
        
        assert result == mock_user
        mock_get_email.assert_called_once_with(mock_db_session, "testuser")
        mock_get_username.assert_called_once_with(mock_db_session, "testuser")
        mock_verify.assert_called_once_with("correct_password", mock_user.hashed_password)
    
    @patch('router.get_user_by_email')
    @patch('router.verify_password')
    def test_authenticate_user_wrong_password(self, mock_verify, mock_get_email, mock_db_session, mock_user):
        """Test authentication failure with wrong password"""
        mock_get_email.return_value = mock_user
        mock_verify.return_value = False  # Wrong password
        
        result = authenticate_user(mock_db_session, "test@example.com", "wrong_password")
        
        assert result is False
        mock_verify.assert_called_once_with("wrong_password", mock_user.hashed_password)
    
    @patch('router.get_user_by_email')
    @patch('router.get_user_by_username')
    def test_authenticate_user_not_found(self, mock_get_username, mock_get_email, mock_db_session):
        """Test authentication failure when user not found"""
        mock_get_email.return_value = None
        mock_get_username.return_value = None
        
        result = authenticate_user(mock_db_session, "nonexistent@example.com", "any_password")
        
        assert result is False
        mock_get_email.assert_called_once()
        mock_get_username.assert_called_once()


class TestIntegrationScenarios:
    """Test realistic authentication scenarios"""
    
    def test_complete_auth_flow(self):
        """Test complete authentication flow with real password hashing"""
        # Step 1: Create a password hash (simulate user registration)
        original_password = "user_password_123"
        hashed_password = get_password_hash(original_password)
        
        # Step 2: Verify password (simulate login)
        assert verify_password(original_password, hashed_password) is True
        assert verify_password("wrong_password", hashed_password) is False
        
        # Step 3: Create tokens (simulate successful login)
        user_data = {"sub": "user@example.com", "user_id": 123}
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)
        
        # Step 4: Verify tokens contain correct data
        access_payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        refresh_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert access_payload["sub"] == "user@example.com"
        assert access_payload["user_id"] == 123
        assert refresh_payload["sub"] == "user@example.com"
        assert refresh_payload["user_id"] == 123
        
        # Step 5: Verify token expiry times are different
        assert access_payload["exp"] < refresh_payload["exp"]
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        # Test with special characters in email
        special_email = "user+test@example-domain.co.uk"
        token = create_access_token({"sub": special_email, "user_id": 1})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == special_email
        
        # Test with very long password
        long_password = "a" * 200
        hashed = get_password_hash(long_password)
        assert verify_password(long_password, hashed) is True
        
        # Test with unicode characters
        unicode_password = "пароль123🔒"
        hashed = get_password_hash(unicode_password)
        assert verify_password(unicode_password, hashed) is True


# Helper function to run tests
if __name__ == "__main__":
    # You can run this file directly to test individual functions
    print("Running auth router unit tests...")
    
    # Quick test of core functions
    password = "test123"
    hashed = get_password_hash(password)
    print(f"Password hashing works: {verify_password(password, hashed)}")
    
    token = create_access_token({"sub": "test@example.com", "user_id": 1})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print(f"Token creation works: {payload['sub'] == 'test@example.com'}")
    
    print("Basic tests passed! Run with pytest for full test suite.")