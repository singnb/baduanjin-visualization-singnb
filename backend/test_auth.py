# test_auth.py
import requests
import json

# Backend API URL
BASE_URL = "http://localhost:8000/api/auth"

def test_register():
    """Test user registration"""
    # Test data
    user_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User"
    }
    
    # Send request
    print(f"Sending POST request to {BASE_URL}/register")
    response = requests.post(f"{BASE_URL}/register", json=user_data)
    print("Register Response Status Code:", response.status_code)
    print("Register Response Content:", response.text[:200])  # Show first 200 chars
    
    try:
        json_response = response.json()
        print("Register Response JSON:", json.dumps(json_response, indent=2))
        return response.status_code == 201
    except json.JSONDecodeError:
        print("Failed to decode JSON response")
        return False

def test_login():
    """Test user login"""
    # Test data
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    # Send request
    print(f"Sending POST request to {BASE_URL}/login")
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    print("Login Response Status Code:", response.status_code)
    
    try:
        json_response = response.json()
        print("Login Response JSON:", json.dumps(json_response, indent=2))
        
        # Save tokens for later use
        if response.status_code == 200:
            with open("tokens.json", "w") as f:
                json.dump(json_response, f, indent=2)
        
        return response.status_code == 200
    except json.JSONDecodeError:
        print("Failed to decode JSON response")
        print("Response content:", response.text[:200])
        return False

# Add the me endpoint test later

if __name__ == "__main__":
    print("Testing Authentication API")
    print("-" * 50)
    
    # Run register test
    print("\nTESTING REGISTER ENDPOINT:")
    register_success = test_register()
    if register_success:
        print("Registration successful!")
    else:
        print("Registration failed or user already exists.")
    
    # Run login test
    print("\nTESTING LOGIN ENDPOINT:")
    login_success = test_login()
    if login_success:
        print("Login successful!")
    else:
        print("Login failed.")