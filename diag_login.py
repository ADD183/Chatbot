
import requests

def test_login():
    url = "http://localhost:8000/auth/login"
    payload = {
        "username": "business@test.com",
        "password": "password123"
    }
    try:
        print(f"Attempting login to {url}...")
        # OAuth2PasswordRequestForm expects data as form-urlencoded
        response = requests.post(url, data=payload, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()
