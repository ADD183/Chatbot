import requests
try:
    r = requests.get('http://localhost:8000/health', timeout=5)
    print('status', r.status_code)
    print(r.text)
except Exception as e:
    print('error', e)
