
import sqlalchemy
from sqlalchemy import create_engine, text

def check_db():
    url = "postgresql://chatbot_user:chatbot_pass@localhost:5432/chatbot_db"
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT email, role FROM users"))
            print("Users in DB:")
            for row in result:
                print(f"- {row[0]} ({row[1]})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
