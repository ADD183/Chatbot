import urllib.request, urllib.parse, json

# Login
login_data = urllib.parse.urlencode({'username': 'user@test.com', 'password': 'password123'}).encode()
login_req = urllib.request.Request('http://localhost:8000/auth/login', data=login_data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
with urllib.request.urlopen(login_req) as resp:
    login_resp = json.load(resp)
    token = login_resp.get('access_token')
    print('Login response:', login_resp)

# Chat
chat_body = json.dumps({
    'message': 'Hello from auth test',
    'session_id': 'test',
    'tenant_name': 'Test Company',
}).encode('utf-8')
chat_req = urllib.request.Request('http://localhost:8000/chat', data=chat_body, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
try:
    with urllib.request.urlopen(chat_req, timeout=60) as resp:
        chat_resp = json.load(resp)
        print('Chat response:', chat_resp)
except Exception as e:
    print('Chat request failed:', repr(e))
