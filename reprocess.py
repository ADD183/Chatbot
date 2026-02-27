
import os
from worker import process_document
from database import SessionLocal
from models import Client, User

def reprocess_files():
    db = SessionLocal()
    client = db.query(Client).filter(Client.name == "Test Company").first()
    if not client:
        print("Client not found")
        return
    
    upload_dir = "uploads"
    files = os.listdir(upload_dir)
    for f in files:
        if f.endswith('.pdf') or f.endswith('.txt'):
            file_path = os.path.join(upload_dir, f)
            print(f"Queueing {f} for client {client.id}...")
            # We call delay to put it back in Celery
            process_document.delay(
                file_path=os.path.abspath(file_path),
                filename=f,
                file_type='pdf' if f.endswith('.pdf') else 'txt',
                client_id=client.id
            )
    db.close()

if __name__ == "__main__":
    reprocess_files()
