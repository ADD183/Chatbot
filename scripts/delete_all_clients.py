"""
Safe deletion script to remove all Client rows via ORM so cascade deletes run.
Run with the project's virtualenv, executed from the project root, e.g.:
.venv\Scripts\python.exe scripts\delete_all_clients.py
"""
import os
import sys

# Ensure project root is on sys.path so local imports work when run from other CWDs
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database import get_db
from models import Client

if __name__ == '__main__':
    db = next(get_db())
    try:
        clients = db.query(Client).all()
        if not clients:
            print('No clients found. Nothing to delete.')
        else:
            print(f'Found {len(clients)} client(s). Deleting...')
            for c in clients:
                print(f' - Deleting client id={c.id} name="{c.name}"')
                try:
                    db.delete(c)
                except Exception as e:
                    print(f'   Failed to delete client id={c.id}: {e}')
            db.commit()
            remaining = db.query(Client).count()
            print(f'Deletion complete. Remaining clients: {remaining}')
    except Exception as e:
        print('Error during deletion:', e)
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()
