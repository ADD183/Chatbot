from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from database import Base
import datetime

class Client(Base):
    """Multi-tenant client table"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    intro = Column(Text, nullable=True)
    website_url = Column(String(500), nullable=True)
    business_description = Column(Text, nullable=True)
    business_logo_url = Column(String(1000), nullable=True)
    welcome_message = Column(Text, nullable=True)
    api_key = Column(String(255), nullable=True)  # Optional client-specific API key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="client", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="client", cascade="all, delete-orphan")
    chat_logs = relationship("ChatLog", back_populates="client", cascade="all, delete-orphan")

class User(Base):
    """User table with RBAC"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'business' or 'user'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    client = relationship("Client", back_populates="users")
    chat_logs = relationship("ChatLog", back_populates="user", cascade="all, delete-orphan")
    
    # Composite index for client_id + username lookups
    __table_args__ = (
        Index('idx_user_client_username', 'client_id', 'username'),
    )

class Document(Base):
    """Document storage with vector embeddings"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # 'pdf' or 'txt'
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position of chunk in document
    embedding = Column(Vector(3072), nullable=False)  # Gemini embeddings produce 3072-dim vectors by default now
    doc_metadata = Column(Text, nullable=True)  # JSON string for additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    client = relationship("Client", back_populates="documents")
    
    # Composite index for client_id + filename lookups
    __table_args__ = (
        Index('idx_document_client_filename', 'client_id', 'filename'),
        Index('idx_document_embedding', 'embedding', postgresql_using='ivfflat', postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )

class ChatLog(Base):
    """Chat history with context tracking"""
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)  # Group related messages
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    context_used = Column(Text, nullable=True)  # Store retrieved context chunks
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    client = relationship("Client", back_populates="chat_logs")
    user = relationship("User", back_populates="chat_logs")
    
    # Composite index for client_id + session_id lookups
    __table_args__ = (
        Index('idx_chatlog_client_session', 'client_id', 'session_id'),
        Index('idx_chatlog_user_session', 'user_id', 'session_id'),
    )


class OtpCode(Base):
    """One-time passcodes for owner authentication"""
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_otp_email_consumed', 'email', 'consumed'),
    )


class EnqueueAudit(Base):
    """Audit table to trace enqueued uploads and worker processing"""
    __tablename__ = "enqueue_audit"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    filename = Column(String(255), nullable=True)
    file_path = Column(String(1000), nullable=True)
    status = Column(String(50), nullable=False, default="enqueued")  # enqueued|started|completed|failed
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    client = relationship("Client")
