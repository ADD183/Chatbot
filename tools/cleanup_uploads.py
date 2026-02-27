import os
import sys

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')

if not os.path.isdir(UPLOAD_DIR):
    print('Uploads directory not found:', UPLOAD_DIR)
    sys.exit(1)

removed = []
errors = []
for fn in os.listdir(UPLOAD_DIR):
    if fn == '.gitkeep':
        continue
    fp = os.path.join(UPLOAD_DIR, fn)
    try:
        if os.path.isfile(fp) or os.path.islink(fp):
            os.remove(fp)
            removed.append(fn)
        elif os.path.isdir(fp):
            # skip directories for safety
            errors.append((fn, 'is a directory'))
    except Exception as e:
        errors.append((fn, str(e)))

print('Removed files:', len(removed))
if removed:
    for f in removed:
        print(' -', f)

if errors:
    print('\nErrors:')
    for fn, err in errors:
        print(' -', fn, ':', err)

print('\nRemaining items in uploads:')
for item in os.listdir(UPLOAD_DIR):
    print(' -', item)
