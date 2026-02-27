
import sqlalchemy
from sqlalchemy import create_engine, text

def check_docs():
    url = "postgresql://chatbot_user:chatbot_pass@localhost:5432/chatbot_db"
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT count(*) FROM documents"))
            count = result.scalar()
            print(f"Total documents chunks: {count}")
            
            result = conn.execute(text("SELECT client_id, filename, count(*) FROM documents GROUP BY client_id, filename"))
            print("Documents per client:")
            for row in result:
                print(f"- Client {row[0]}: {row[1]} ({row[2]} chunks)")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_docs()
