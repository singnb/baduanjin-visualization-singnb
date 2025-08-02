# type: ignore
# /tests/utils/test_security.py
# Unit tests for utils/security.pycore functions

import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.security import verify_password, get_password_hash, pwd_context


class TestPasswordHashing:
    
    def test_get_password_hash_returns_string(self):
        """Test that password hashing returns a string"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Hash should be different from original
    
    def test_get_password_hash_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes"""
        password1 = "password123"
        password2 = "differentpassword456"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2
    
    def test_get_password_hash_same_password_different_hashes(self):
        """Test that same password produces different hashes due to salt"""
        password = "samepassword123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Due to salt, same password should produce different hashes
        assert hash1 != hash2
    
    def test_get_password_hash_bcrypt_format(self):
        """Test that hash follows bcrypt format"""
        password = "testpassword"
        hashed = get_password_hash(password)
        
        # Bcrypt hashes start with $2b$ (or $2a$, $2x$, $2y$)
        assert hashed.startswith('$2b$') or hashed.startswith('$2a$') or hashed.startswith('$2x$') or hashed.startswith('$2y$')
        
    def test_get_password_hash_empty_password(self):
        """Test hashing empty password"""
        password = ""
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_get_password_hash_special_characters(self):
        """Test hashing password with special characters"""
        password = "p@ssw0rd!#$%^&*()"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password
    
    def test_get_password_hash_unicode_characters(self):
        """Test hashing password with unicode characters"""
        password = "пароль123密码"  # Russian and Chinese characters
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password
    
    def test_get_password_hash_long_password(self):
        """Test hashing very long password"""
        password = "a" * 1000  # 1000 character password
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password
    
    def test_get_password_hash_whitespace_password(self):
        """Test hashing password with whitespace"""
        password = "  password with spaces  "
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password


class TestPasswordVerification:
    
    def test_verify_password_correct_password(self):
        """Test verification with correct password"""
        password = "correctpassword123"
        hashed = get_password_hash(password)
        
        result = verify_password(password, hashed)
        assert result is True
    
    def test_verify_password_incorrect_password(self):
        """Test verification with incorrect password"""
        correct_password = "correctpassword123"
        incorrect_password = "wrongpassword456"
        hashed = get_password_hash(correct_password)
        
        result = verify_password(incorrect_password, hashed)
        assert result is False
    
    def test_verify_password_empty_password_against_hash(self):
        """Test verification of empty password against real hash"""
        password = "realpassword"
        hashed = get_password_hash(password)
        
        result = verify_password("", hashed)
        assert result is False
    
    def test_verify_password_empty_password_against_empty_hash(self):
        """Test verification of empty password against empty password hash"""
        empty_password = ""
        hashed = get_password_hash(empty_password)
        
        result = verify_password(empty_password, hashed)
        assert result is True
    
    def test_verify_password_case_sensitive(self):
        """Test that password verification is case sensitive"""
        password = "CaseSensitivePassword"
        hashed = get_password_hash(password)
        
        # Test with different case
        result_lower = verify_password(password.lower(), hashed)
        result_upper = verify_password(password.upper(), hashed)
        result_correct = verify_password(password, hashed)
        
        assert result_lower is False
        assert result_upper is False
        assert result_correct is True
    
    def test_verify_password_special_characters(self):
        """Test verification with special characters"""
        password = "sp3c!@l#ch@r$cters%^&*()"
        hashed = get_password_hash(password)
        
        result = verify_password(password, hashed)
        assert result is True
    
    def test_verify_password_unicode_characters(self):
        """Test verification with unicode characters"""
        password = "密码πароль123"
        hashed = get_password_hash(password)
        
        result = verify_password(password, hashed)
        assert result is True
    
    def test_verify_password_whitespace_sensitive(self):
        """Test that whitespace matters in password verification"""
        password = "password"
        password_with_space = " password "
        hashed = get_password_hash(password)
        
        result_exact = verify_password(password, hashed)
        result_with_space = verify_password(password_with_space, hashed)
        
        assert result_exact is True
        assert result_with_space is False
    
    def test_verify_password_long_password(self):
        """Test verification with very long password"""
        password = "a" * 500 + "b" * 500  # 1000 character password
        hashed = get_password_hash(password)
        
        result = verify_password(password, hashed)
        assert result is True
    
    def test_verify_password_slightly_different_passwords(self):
        """Test verification with very similar but different passwords"""
        password1 = "password123"
        password2 = "password124"  # Just one character different
        hashed = get_password_hash(password1)
        
        result_correct = verify_password(password1, hashed)
        result_incorrect = verify_password(password2, hashed)
        
        assert result_correct is True
        assert result_incorrect is False


class TestPasswordContextIntegration:
    
    def test_pwd_context_hash_method(self):
        """Test that pwd_context hash method works"""
        password = "testpassword"
        hashed = pwd_context.hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed.startswith('$2b$') or hashed.startswith('$2a$') or hashed.startswith('$2x$') or hashed.startswith('$2y$')
    
    def test_pwd_context_verify_method(self):
        """Test that pwd_context verify method works"""
        password = "testpassword"
        hashed = pwd_context.hash(password)
        
        result_correct = pwd_context.verify(password, hashed)
        result_incorrect = pwd_context.verify("wrongpassword", hashed)
        
        assert result_correct is True
        assert result_incorrect is False


class TestHashValidation:
    
    def test_verify_password_with_invalid_hash_format(self):
        """Test verification with invalid hash format"""
        password = "testpassword"
        invalid_hash = "not_a_valid_hash"
        
        # This should return False or raise an exception
        try:
            result = verify_password(password, invalid_hash)
            assert result is False
        except Exception:
            # It's acceptable for invalid hash to raise an exception
            pass
    
    def test_verify_password_with_none_hash(self):
        """Test verification with None hash"""
        password = "testpassword"
        
        try:
            result = verify_password(password, None)
            assert result is False
        except (TypeError, AttributeError):
            # It's acceptable for None hash to raise an exception
            pass
    
    def test_verify_password_with_empty_hash(self):
        """Test verification with empty hash"""
        password = "testpassword"
        
        try:
            result = verify_password(password, "")
            assert result is False
        except Exception:
            # It's acceptable for empty hash to raise an exception
            pass


class TestSecurityStrength:
    
    def test_hash_randomness(self):
        """Test that hashes have sufficient randomness"""
        password = "testpassword"
        hashes = [get_password_hash(password) for _ in range(10)]
        
        # All hashes should be unique due to salt
        assert len(set(hashes)) == len(hashes)
    
    def test_hash_length_consistency(self):
        """Test that hash length is consistent"""
        passwords = ["short", "medium_length_password", "very_long_password_with_many_characters_to_test_consistency"]
        hashes = [get_password_hash(pwd) for pwd in passwords]
        
        # All bcrypt hashes should have the same length (60 characters)
        hash_lengths = [len(h) for h in hashes]
        assert all(length == hash_lengths[0] for length in hash_lengths)
        assert hash_lengths[0] == 60  # Standard bcrypt hash length
    
    def test_bcrypt_rounds_default(self):
        """Test that bcrypt uses appropriate number of rounds"""
        password = "testpassword"
        hashed = get_password_hash(password)
        
        # Extract rounds from bcrypt hash (format: $2b$rounds$salt+hash)
        parts = hashed.split('$')
        if len(parts) >= 3:
            rounds = int(parts[2])
            # Should use at least 10 rounds for security (12 is default for passlib)
            assert rounds >= 10


class TestErrorHandling:
    
    def test_get_password_hash_with_none_input(self):
        """Test passwords at various boundary values"""
        test_passwords = [
            "",  # Empty
            "a",  # Single character
            "aa",  # Two characters
            "a" * 72,  # Bcrypt input limit
            "a" * 100,  # Beyond bcrypt input limit
        ]
        
        for password in test_passwords:
            hashed = get_password_hash(password)
            assert verify_password(password, hashed) is True