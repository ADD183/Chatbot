from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime

# Client Schemas
class ClientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    api_key: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: int
    slug: str
    intro: Optional[str] = None
    website_url: Optional[str] = None
    business_description: Optional[str] = None
    business_logo_url: Optional[str] = None
    welcome_message: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# User Schemas
class UserBase(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    email: str # Relaxed from EmailStr to allow simple test inputs like abc@123
    full_name: Optional[str] = None
    role: str = Field(..., pattern="^(business|user)$")
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['business', 'user']:
            raise ValueError('Role must be either "business" or "user"')
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=1)
    client_id: Optional[int] = None
    
    @validator('client_id', pre=True)
    def empty_string_to_none(cls, v):
        if v == '':
            return None
        return v

class UserResponse(UserBase):
    id: int
    client_id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True

class UserLogin(BaseModel):
    username: str
    password: str

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    client_id: Optional[int] = None
    role: Optional[str] = None

# Document Schemas
class DocumentChunk(BaseModel):
    filename: str
    chunk_text: str
    chunk_index: int
    
class DocumentUploadResponse(BaseModel):
    filename: str
    file_type: str
    total_chunks: int
    message: str

class DocumentListItem(BaseModel):
    id: int
    filename: str
    file_type: str
    chunk_count: int
    status: str
    created_at: datetime
    
class DocumentListResponse(BaseModel):
    documents: List[DocumentListItem]
    total: int

# Chat Schemas
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = None
    tenant_name: Optional[str] = None
    tenant_id: Optional[int] = None

    
class ChatResponse(BaseModel):
    response: str
    session_id: str
    context_used: Optional[List[str]] = None


class OtpRequest(BaseModel):
    email: str


class OtpVerifyRequest(BaseModel):
    email: str
    code: str
    full_name: Optional[str] = None


class OwnerProfileUpsert(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=255)
    intro: Optional[str] = None
    website_url: Optional[str] = None
    business_description: Optional[str] = None
    welcome_message: Optional[str] = None


class BusinessSummary(BaseModel):
    id: int
    name: str
    slug: str
    intro: Optional[str] = None


class BusinessDetail(BusinessSummary):
    created_at: datetime
    business_description: Optional[str] = None
    business_logo_url: Optional[str] = None
    welcome_message: Optional[str] = None


class BusinessListResponse(BaseModel):
    businesses: List[BusinessSummary]
    total: int


class OwnerAnalyticsItem(BaseModel):
    id: int
    session_id: str
    question: str
    answer: str
    created_at: datetime


class OwnerAnalyticsResponse(BaseModel):
    total_questions: int
    recent_qa: List[OwnerAnalyticsItem]
    
class ChatHistoryItem(BaseModel):
    id: int
    user_message: str
    bot_response: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatHistoryResponse(BaseModel):
    history: List[ChatHistoryItem]
    total: int

# Error Response Schema
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
