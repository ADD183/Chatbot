from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://chatbot_user:chatbot_pass@localhost:5432/chatbot_db")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False
)

# Enable pgvector extension
def enable_pgvector(dbapi_conn, connection_record):
    """Enable pgvector extension on connection"""
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        dbapi_conn.commit()
    except Exception as e:
        print(f"Error enabling pgvector: {e}")
        dbapi_conn.rollback()
    finally:
        cursor.close()

# Register the event listener
event.listen(engine, "connect", enable_pgvector)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for getting database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    from models import Client, User, Document, ChatLog, EnqueueAudit
    # In development, we might want to drop and recreate for schema changes
    # if os.getenv("ENVIRONMENT") == "development":
    #     print("Dropping all tables (Development mode)...")
    #     Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")
