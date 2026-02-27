import os, socket, traceback

print('GEMINI_API_KEY present:', bool(os.getenv('GEMINI_API_KEY')))
print('MOCK_GEMINI:', os.getenv('MOCK_GEMINI'))

# Test TCP connectivity to Google Generative API
hosts = ['generative.googleapis.com', 'www.googleapis.com', 'www.google.com']
for h in hosts:
    try:
        s = socket.create_connection((h, 443), timeout=5)
        s.close()
        print(f'CONNECT_OK {h}:443')
    except Exception as e:
        print(f'CONNECT_ERR {h}:443 ->', repr(e))

# Test importing genai and creating client
try:
    from google import genai
    print('genai_import_ok')
    try:
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        print('genai_client_created')
        try:
            models = list(client.models.list())
            print('models_count', len(models))
            for m in models[:10]:
                try:
                    name = getattr(m, 'name', None) or (m.get('name') if isinstance(m, dict) else None)
                    print('model:', name)
                except Exception:
                    print('model_repr:', m)
        except Exception as e:
            print('list_models_error:')
            traceback.print_exc()
    except Exception as e:
        print('client_creation_error:')
        traceback.print_exc()
except Exception as e:
    print('import_genai_error:')
    traceback.print_exc()
