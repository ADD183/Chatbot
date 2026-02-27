import os
import time
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['MOCK_GEMINI'] = 'true'

from worker import process_document

uploads = os.path.join(os.path.dirname(__file__), '..', 'uploads')
uploads = os.path.abspath(uploads)
os.makedirs(uploads, exist_ok=True)

file_path = os.path.join(uploads, f'test_manual_{int(time.time())}.txt')
with open(file_path, 'w', encoding='utf-8') as f:
    f.write('This is a manual test. Supervised, unsupervised, reinforcement.')

print('Created file:', file_path)

try:
    res = process_document.run(None, file_path=file_path, filename=os.path.basename(file_path), file_type='txt', client_id=1)
    print('Task returned:', res)
except Exception as e:
    print('Task raised exception:', e)

print('Done')
