
import requests
import json

BASE_URL = "http://localhost:8000"

def test_flow():
    # 1. Login
    print("Testing Login...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "user@test.com", "password": "password123"})
        if resp.status_code != 200:
            print(f"Login Failed: {resp.status_code} - {resp.text}")
            return
        token = resp.json()["access_token"]
        print("Login Success!")
    except Exception as e:
        print(f"Login Exception: {e}")
        return

    # 2. Test Chat
    print("\nTesting Chat...")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "message": "Hello from debug script",
        "session_id": "debug-session-123",
        "tenant_name": "Test Company"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/chat", headers=headers, json=payload)
        if resp.status_code == 200:
            print("Chat Success!")
            print(resp.json())
        else:
            print(f"Chat Failed: {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"Chat Exception: {e}")

if __name__ == "__main__":
    test_flow()
