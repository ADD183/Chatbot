import urllib.request, json

data = json.dumps({"message": "Hello from test script","session_id": "test","tenant_id": 1, "tenant_name": "Test Company"}).encode('utf-8')
req = urllib.request.Request('http://localhost:8000/public/chat', data=data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as resp:
    print(resp.read().decode())
