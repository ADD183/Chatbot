#!/usr/bin/env python3
import requests
import json
import time

# Register a business user
unique = str(int(time.time()))[-6:]
email = f'biz_{unique}@example.com'

print(f"Registering business user: {email}")
register_resp = requests.post('http://localhost:8000/auth/register', json={
    'email': email,
    'password': 'Test123!',
    'full_name': 'Admin',
    'role': 'business'
})

if register_resp.status_code != 200:
    print(f'Register failed: {register_resp.status_code}')
    print(register_resp.text)
    exit(1)

token = register_resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

print("\nChecking documents...")
resp = requests.get('http://localhost:8000/documents/', headers=headers)
print(f'Status: {resp.status_code}')

if resp.status_code != 200:
    print(f'Error: {resp.text}')
    exit(1)

data = resp.json()
total = data.get('total', 0)
docs = data.get('documents', [])

print(f'\n========== KNOWLEDGE BASE STATUS ==========')
print(f'Total documents: {total}')
print(f'Documents list ({len(docs)} items):')

if len(docs) == 0:
    print('  [EMPTY - No documents in knowledge base]')
else:
    for i, doc in enumerate(docs[:15], 1):
        status = doc.get('status', 'unknown')
        chunks = doc.get('chunk_count', 0)
        created = doc.get('created_at', 'unknown')
        print(f'  {i}. {doc.get("filename", "unknown")}')
        print(f'     Status: {status} | Chunks: {chunks} | Created: {created}')

print('\n========== INTERPRETATION ==========')
if total == 0:
    print('➜ Knowledge base is EMPTY')
    print('➜ You need to upload documents via the upload endpoint')
elif total < 5:
    print(f'➜ Only {total} document(s) in system')
    print('➜ Check if your ML/PDF files were uploaded successfully')
else:
    print(f'➜ {total} documents in system')
    print('➜ Check file names to verify they are your ML/PDF files')
