import requests, time
BASE='http://localhost:8000'
email=f'business_test_{int(time.time())}@example.com'
payload={'username': None, 'email': email, 'password':'Pass123!', 'role':'business'}
print('Registering', email)
r=requests.post(f'{BASE}/auth/register', json=payload)
print('status', r.status_code)
print(r.text)
