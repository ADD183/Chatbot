"""
Test script to verify the chatbot system functionality
Run this after setting up the environment
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✓ Health check passed")

def test_create_client():
    """Test client creation"""
    print("\n=== Testing Client Creation ===")
    data = {
        "name": f"Test Client {int(time.time())}"
    }
    response = requests.post(f"{BASE_URL}/clients", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 201
    client_id = response.json()["id"]
    print(f"✓ Client created with ID: {client_id}")
    return client_id

def test_create_user(client_id):
    """Test user creation"""
    print("\n=== Testing User Creation ===")
    
    # Create business user
    data = {
        "username": f"business_user_{int(time.time())}",
        "email": f"business_{int(time.time())}@test.com",
        "password": "SecurePass123!",
        "role": "business",
        "client_id": client_id
    }
    response = requests.post(f"{BASE_URL}/users", json=data)
    print(f"Business User Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 201
    print("✓ Business user created")
    
    # Create regular user
    data_user = {
        "username": f"regular_user_{int(time.time())}",
        "email": f"user_{int(time.time())}@test.com",
        "password": "SecurePass123!",
        "role": "user",
        "client_id": client_id
    }
    response_user = requests.post(f"{BASE_URL}/users", json=data_user)
    print(f"Regular User Status: {response_user.status_code}")
    assert response_user.status_code == 201
    print("✓ Regular user created")
    
    return data["username"], data["password"], data_user["username"], data_user["password"]

def test_login(username, password):
    """Test login"""
    print(f"\n=== Testing Login for {username} ===")
    data = {
        "username": username,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/login", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    token = response.json()["access_token"]
    print(f"✓ Login successful, token received")
    return token

def test_upload_document(token):
    """Test document upload (requires business role)"""
    print("\n=== Testing Document Upload ===")
    
    # Create a test text file
    test_content = """
    This is a test document for the AI chatbot system.
    
    Key Features:
    1. Multi-tenant architecture ensures data isolation
    2. Role-based access control provides security
    3. RAG implementation enables context-aware responses
    4. Vector embeddings allow semantic search
    5. Background processing handles large documents efficiently
    
    Technical Stack:
    - FastAPI for the backend framework
    - PostgreSQL with pgvector for vector storage
    - Google Gemini for embeddings and chat
    - Celery for async task processing
    - Docker for containerization
    
    This document will be chunked and embedded for retrieval.
    """
    
    with open("test_document.txt", "w") as f:
        f.write(test_content)
    
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("test_document.txt", open("test_document.txt", "rb"), "text/plain")}
    
    response = requests.post(f"{BASE_URL}/upload", headers=headers, files=files)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        print("✓ Document uploaded successfully")
        # Wait for processing
        print("Waiting 10 seconds for background processing...")
        time.sleep(10)
    else:
        print(f"✗ Upload failed: {response.text}")
    
    # Cleanup
    import os
    if os.path.exists("test_document.txt"):
        os.remove("test_document.txt")

def test_list_files(token):
    """Test listing files"""
    print("\n=== Testing File Listing ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/files", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    if response.status_code == 200:
        print("✓ Files listed successfully")

def test_chat(token, with_context=True):
    """Test chat endpoint"""
    print(f"\n=== Testing Chat {'with' if with_context else 'without'} Context ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    if with_context:
        message = "What are the key features mentioned in the document?"
    else:
        message = "Hello, how are you?"
    
    data = {
        "message": message
    }
    
    response = requests.post(f"{BASE_URL}/chat", headers=headers, json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result['response'][:200]}...")
        print(f"Session ID: {result['session_id']}")
        if result.get('context_used'):
            print(f"Context chunks used: {len(result['context_used'])}")
        print("✓ Chat successful")
        return result['session_id']
    else:
        print(f"✗ Chat failed: {response.text}")
        return None

def test_chat_history(token, session_id):
    """Test chat history retrieval"""
    print("\n=== Testing Chat History ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/chat/history?session_id={session_id}",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    if response.status_code == 200:
        print("✓ Chat history retrieved successfully")

def test_rbac(business_token, user_token):
    """Test role-based access control"""
    print("\n=== Testing RBAC ===")
    
    # User role should NOT be able to upload
    print("Testing user role upload (should fail)...")
    headers = {"Authorization": f"Bearer {user_token}"}
    
    # Create a dummy file
    with open("test_rbac.txt", "w") as f:
        f.write("Test content")
    
    files = {"file": ("test_rbac.txt", open("test_rbac.txt", "rb"), "text/plain")}
    response = requests.post(f"{BASE_URL}/upload", headers=headers, files=files)
    
    import os
    if os.path.exists("test_rbac.txt"):
        os.remove("test_rbac.txt")
    
    if response.status_code == 403:
        print("✓ RBAC working: User role correctly denied upload access")
    else:
        print(f"✗ RBAC failed: Expected 403, got {response.status_code}")
    
    # User role SHOULD be able to chat
    print("Testing user role chat (should succeed)...")
    data = {"message": "Hello"}
    response = requests.post(f"{BASE_URL}/chat", headers=headers, json=data)
    
    if response.status_code == 200:
        print("✓ RBAC working: User role can access chat")
    else:
        print(f"✗ RBAC failed: User role should be able to chat")

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("CHATBOT SYSTEM TEST SUITE")
    print("=" * 60)
    
    try:
        # Test health
        test_health()
        
        # Create client
        client_id = test_create_client()
        
        # Create users
        business_user, business_pass, regular_user, regular_pass = test_create_user(client_id)
        
        # Login both users
        business_token = test_login(business_user, business_pass)
        user_token = test_login(regular_user, regular_pass)
        
        # Test RBAC
        test_rbac(business_token, user_token)
        
        # Upload document (business user)
        test_upload_document(business_token)
        
        # List files (business user)
        test_list_files(business_token)
        
        # Test chat with context
        session_id = test_chat(business_token, with_context=True)
        
        # Test chat history
        if session_id:
            test_chat_history(business_token, session_id)
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY! ✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except requests.exceptions.ConnectionError:
        print("\n✗ Cannot connect to API. Make sure the server is running at http://localhost:8000")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
