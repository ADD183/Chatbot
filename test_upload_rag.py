#!/usr/bin/env python3
"""
Test document upload and RAG retrieval
"""
import requests
import json
import time
import os

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("DOCUMENT UPLOAD & RAG TEST")
print("=" * 70)

# Step 1: Register business user
print("\n[1] Registering business user...")
unique = str(int(time.time()))[-6:]
email = f'biz_{unique}@example.com'

register_resp = requests.post(f'{BASE_URL}/auth/register', json={
    'email': email,
    'password': 'Test123!',
    'full_name': 'Admin',
    'role': 'business'
})

if register_resp.status_code != 200:
    print(f"❌ Error: {register_resp.status_code}")
    print(register_resp.text)
    exit(1)

token = register_resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print(f"✓ Registered: {email}")

# Step 2: Check pre-upload document count
print("\n[2] Checking initial document count...")
resp = requests.get(f'{BASE_URL}/documents/', headers=headers)
initial_count = resp.json().get('total', 0)
print(f"✓ Initial count: {initial_count} documents")

# Step 3: Create and upload a test document
print("\n[3] Creating test document...")
test_content = """
MACHINE LEARNING FUNDAMENTALS

Machine Learning is a subset of Artificial Intelligence that enables computer systems to learn and improve from experience without explicit programming.

KEY MACHINE LEARNING CONCEPTS:

1. SUPERVISED LEARNING
   - Uses labeled training data
   - Goal is to predict outputs for new inputs
   - Examples: Linear Regression, Decision Trees, SVMs
   - Applications: Email spam detection, credit scoring

2. UNSUPERVISED LEARNING
   - Works with unlabeled data
   - Discovers hidden patterns and structures
   - Examples: K-means clustering, Hierarchical clustering, PCA
   - Applications: Customer segmentation, anomaly detection

3. REINFORCEMENT LEARNING
   - Agent learns through interaction with environment
   - Receives rewards/penalties for actions
   - Examples: Q-learning, Policy Gradient
   - Applications: Game AI, Robotics, Autonomous vehicles

MACHINE LEARNING IN BANKING:

- CREDIT RISK PREDICTION: Supervised models predict borrower default likelihood
- FRAUD DETECTION: Unsupervised anomaly detection identifies suspicious transactions
- CUSTOMER SEGMENTATION: Clustering for targeted marketing campaigns
- LOAN APPROVAL: Classification models for instant loan decisions
"""

import tempfile
temp_dir = tempfile.gettempdir()
test_file = os.path.join(temp_dir, 'test_ml_doc.txt')

with open(test_file, 'w') as f:
    f.write(test_content)
print(f"✓ Created test file: {os.path.basename(test_file)}")

# Step 4: Upload document
print("\n[4] Uploading document...")
with open(test_file, 'rb') as f:
    files = {'file': ('test_ml_doc.txt', f, 'text/plain')}
    upload_resp = requests.post(f'{BASE_URL}/documents/upload', files=files, headers=headers)

if upload_resp.status_code not in [200, 201]:
    print(f"❌ Upload failed: {upload_resp.status_code}")
    print(upload_resp.text[:500])
    exit(1)

upload_data = upload_resp.json()
print(f"✓ Upload successful")
print(f"  - Total chunks: {upload_data.get('total_chunks', '?')}")
print(f"  - Message: {upload_data.get('message', '')}")

# Step 5: Wait for background processing
print("\n[5] Waiting for embeddings to process (15 seconds)...")
time.sleep(15)

# Step 6: Check if document was added to database
print("\n[6] Checking document count after upload...")
resp = requests.get(f'{BASE_URL}/documents/', headers=headers)
final_count = resp.json().get('total', 0)
print(f"✓ Final count: {final_count} documents")
print(f"  Added: {final_count - initial_count} new document(s)")

# List the documents
docs = resp.json().get('documents', [])
if docs:
    print(f"\n  Documents in system:")
    for doc in docs[-5:]:  # Show last 5
        print(f"    - {doc.get('filename')} ({doc.get('chunk_count', 0)} chunks, {doc.get('status')})")

# Step 7: Test RAG - Chat about ML
print("\n[7] Testing RAG - Chat about Machine Learning...")
chat_resp = requests.post(f'{BASE_URL}/chat', json={
    'message': 'What are the types of machine learning?',
    'tenant_name': f'tenant_{unique}'
}, headers=headers)

if chat_resp.status_code == 200:
    response = chat_resp.json().get('message', '')
    print(f"✓ Chat response received ({len(response)} chars)")
    print(f"\n  Bot says:\n  {response[:500]}...")
    
    # Check if response includes ML types from our document
    lcresp = response.lower()
    if any(term in lcresp for term in ['supervised', 'unsupervised', 'reinforcement']):
        print(f"\n  ✓✓ SUCCESS: Bot knows about machine learning types from uploaded document!")
    else:
        print(f"\n  ⚠ Response doesn't mention ML types - may not have accessed the document")
else:
    print(f"❌ Chat failed: {chat_resp.status_code}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
