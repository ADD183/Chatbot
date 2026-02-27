import sys
import json

# Ensure the project root is on sys.path when running inside the container
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

from gemini_service import gemini_service

if __name__ == '__main__':
    try:
        res = gemini_service.generate_chat_response("Hello from local test")
        print(json.dumps(res, ensure_ascii=False))
    except Exception as e:
        import traceback
        traceback.print_exc()
