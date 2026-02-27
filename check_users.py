
from database import get_db, init_db
from models import User
from sqlalchemy.orm import Session

# Initialize DB (just in case)
init_db()

db = next(get_db())

print("--- Users in DB ---")
users = db.query(User).all()
for user in users:
    print(f"ID: {user.id}, Username: {user.username}, Email: {user.email}, Role: {user.role}, Active: {user.is_active}")

print("-------------------")
