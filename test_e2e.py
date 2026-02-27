#!/usr/bin/env python3
"""
End-to-end test of the chatbot:
1. Register/Login
2. Chat with bot
3. Check what information the bot knows about
"""

import requests
import json
import time
import os
from urllib.parse import urlencode

BASE_URL = "http://localhost:8000"

# Use unique tenant/email combo for clean test
UNIQUE_ID = str(int(time.time()))[-6:]
TENANT_NAME = f"test_tenant_{UNIQUE_ID}"
EMAIL = f"testuser_{UNIQUE_ID}@example.com"
PASSWORD = "TestPass123!"

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log(msg):
    print(msg)

def step(num, msg):
    print(f"\n{BLUE}[Step {num}]{RESET} {msg}")

def success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def error(msg):
    print(f"{RED}✗{RESET} {msg}")

def info(msg):
    print(f"{YELLOW}ℹ{RESET} {msg}")

# ========== STEP 1: REGISTER ==========
step(1, "Register new user")

register_payload = {
    "email": EMAIL,
    "password": PASSWORD,
    "full_name": "Test User",
    "role": "user"
}

try:
    resp = requests.post(f"{BASE_URL}/auth/register", json=register_payload)
    if resp.status_code == 200:
        success("User registered")
        data = resp.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        print(f"  Email: {EMAIL}")
    else:
        error(f"Register failed: {resp.status_code}")
        print(f"  {resp.text[:300]}")
        exit(1)
except Exception as e:
    error(f"Request failed: {e}")
    exit(1)

headers = {"Authorization": f"Bearer {access_token}"}
print(f"  Token: {access_token[:40]}...")

# ========== STEP 2: CHAT - ASK FOR INFORMATION ==========
step(2, "Chat: Ask 'What information do you have?'")

chat_payload = {
    "message": "What information do you have?",
    "tenant_name": TENANT_NAME
}

try:
    resp = requests.post(f"{BASE_URL}/chat", json=chat_payload, headers=headers)
    if resp.status_code == 200:
        success("Chat request succeeded")
        data = resp.json()
        response = data.get("message") or data.get("response")
        print(f"\n  Bot Response:\n")
        print(f"  {response}\n")
    else:
        error(f"Chat failed: {resp.status_code}")
        print(f"  {resp.text[:500]}")
except Exception as e:
    error(f"Chat request failed: {e}")

# ========== STEP 3: CHAT - ASK ABOUT ML ==========
step(3, "Chat: Ask about machine learning")

chat_payload2 = {
    "message": "Tell me about machine learning types",
    "tenant_name": TENANT_NAME
}

try:
    resp = requests.post(f"{BASE_URL}/chat", json=chat_payload2, headers=headers)
    if resp.status_code == 200:
        success("Chat request succeeded")
        data = resp.json()
        response = data.get("message") or data.get("response")
        print(f"\n  Bot Response:\n")
        print(f"  {response}\n")
        
        # Check if response mentions ML types
        lcresp = response.lower()
        if any(term in lcresp for term in ["supervised", "unsupervised", "reinforcement"]):
            success("Response contains ML-specific terms!")
        else:
            info("Response does not mention ML types specifically")
except Exception as e:
    error(f"Chat request failed: {e}")

# ========== STEP 4: CHECK DOCUMENTS VIA API ==========
step(4, "Check stored documents")

try:
    resp = requests.get(f"{BASE_URL}/docs", headers=headers)
    if resp.status_code == 200:
        success("Retrieved documents list")
        docs = resp.json()
        if isinstance(docs, list):
            doc_count = len(docs)
        elif isinstance(docs, dict) and "documents" in docs:
            doc_count = len(docs.get("documents", []))
        else:
            doc_count = 0
        
        print(f"  Documents stored: {doc_count}")
        if doc_count > 0 and isinstance(docs, list):
            for i, doc in enumerate(docs[:3]):
                print(f"    {i+1}. {doc.get('filename', 'unknown')}")
        elif doc_count > 0 and isinstance(docs, dict):
            for i, doc in enumerate(docs.get("documents", [])[:3]):
                print(f"    {i+1}. {doc.get('filename', 'unknown')}")
    elif resp.status_code == 404:
        info("No /docs endpoint found")
    else:
        error(f"API error: {resp.status_code}")
except Exception as e:
    info(f"Could not check documents: {e}")

# ========== SUMMARY ==========
print(f"\n{BLUE}{'='*60}{RESET}")
print(f"{BLUE}Test Complete{RESET}")
print(f"{BLUE}{'='*60}{RESET}")
print("""
Questions to answer:
1. Does the bot know about your uploaded ML/PDF documents?
   - If response mentions "supervised", "unsupervised", "reinforcement" → YES
   - If response is generic → Check the document list above

2. Is there old data in the knowledge base?
   - Check what documents are listed in Step 4
   - If documents from before your upload are there → YES there's old data
   
3. Are new uploads being indexed?
   - Upload a new document and ask about it in a new chat
   - If the bot knows about it → indexing works
""")
