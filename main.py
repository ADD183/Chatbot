from urllib import request
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query, APIRouter, Request
from urllib.parse import urlparse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from datetime import timedelta
from datetime import datetime, timezone
import logging
import os
import uuid
from typing import List, Optional
import shutil
import random
import re
from dotenv import load_dotenv
from sqlalchemy import text
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup


load_dotenv()

# Configure allowed CORS origins from environment (comma-separated)
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _allowed_origins.split(",") if o.strip()]

from database import get_db, init_db
from models import Client, User, Document, ChatLog, OtpCode
from schemas import (
    ClientCreate, ClientResponse,
    UserCreate, UserResponse, UserLogin,
    Token, ChatRequest, ChatResponse,
    DocumentUploadResponse, DocumentListResponse, DocumentListItem,
    ChatHistoryResponse, ChatHistoryItem,
    ErrorResponse,
    OtpRequest, OtpVerifyRequest, OwnerProfileUpsert,
    BusinessSummary, BusinessDetail, BusinessListResponse,
    OwnerAnalyticsItem, OwnerAnalyticsResponse
)
from auth import (
    get_password_hash, authenticate_user, create_access_token,
    get_current_user, require_business_role, require_any_role,
    get_optional_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, create_refresh_token, verify_refresh_token
)
from gemini_service import gemini_service
from worker import process_document, chunk_text

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Tenant AI Chatbot API",
    description="Production-ready FastAPI backend with RAG using Google Gemini and PostgreSQL pgvector",
    version="1.0.0"
)

logger = logging.getLogger(__name__)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # configure trusted origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_errors(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 422:
        logger.debug("422 Error at %s", request.url.path)
    return response

# Upload directory - use absolute path for consistency across processes
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Static directory for serving uploaded assets (logos)
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
LOGO_DIR = os.path.join(STATIC_DIR, "logos")
os.makedirs(LOGO_DIR, exist_ok=True)

# Serve static files (logos/uploads) at /static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def slugify_business_name(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base or "business"


def unique_slug(db: Session, name: str, exclude_client_id: Optional[int] = None) -> str:
    base = slugify_business_name(name)
    candidate = base
    counter = 1
    while True:
        query = db.query(Client).filter(Client.slug == candidate)
        if exclude_client_id is not None:
            query = query.filter(Client.id != exclude_client_id)
        if not query.first():
            return candidate
        counter += 1
        candidate = f"{base}-{counter}"


def generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def extract_text_from_url(url: str) -> str:
    parsed = urlparse(url)
    # Allow users to submit raw hostnames (without scheme). Default to https://
    if not parsed.scheme:
        url = 'https://' + url
        parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are supported")
    # Use a requests Session with retries and a browser-like user-agent to avoid blocks
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))

    headers = {
        'User-Agent': os.getenv('SCRAPER_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                              '(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    try:
        resp = session.get(url, timeout=20, headers=headers, allow_redirects=True)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed fetching URL: {e}")

    # Try to decode response text
    body = resp.text
    if not body:
        raise ValueError("Fetched page is empty")

    soup = BeautifulSoup(body, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "meta", "link"]):
        try:
            tag.decompose()
        except Exception:
            pass

    text_content = " ".join(soup.get_text(separator=" ").split())
    if not text_content or len(text_content.strip()) < 20:
        raise ValueError("No readable text found at URL or content too short")
    return text_content


def ingest_website_kb(db: Session, client_id: int, website_url: str) -> int:
    text_content = extract_text_from_url(website_url)
    chunks = chunk_text(text_content)

    # Remove any existing documents for this URL for this client
    try:
        db.query(Document).filter(
            Document.client_id == client_id,
            Document.filename == website_url
        ).delete(synchronize_session=False)
    except Exception as e:
        logger.warning("Failed to delete existing documents for %s: %s", website_url, e)

    chunk_texts = [chunk_tuple[0] for chunk_tuple in chunks]
    embeddings = []
    if chunk_texts:
        try:
            embeddings = gemini_service.generate_embeddings(chunk_texts)
        except Exception as e:
            logger.warning("Error generating embeddings for website chunks: %s", e)
            embeddings = [[] for _ in chunk_texts]

    for idx, chunk_tuple in enumerate(chunks):
        chunk, start_char, end_char = chunk_tuple
        emb = embeddings[idx] if idx < len(embeddings) and embeddings[idx] else []
        metadata = f'{{"source":"website","start_char":{start_char},"end_char":{end_char}}}'
        try:
            db.add(Document(
                client_id=client_id,
                filename=website_url,
                file_type="url",
                chunk_text=chunk,
                chunk_index=idx,
                embedding=[float(x) for x in emb] if emb else None,
                doc_metadata=metadata
            ))
        except Exception as e:
            logger.exception("Failed to add Document chunk to DB: %s", e)

    return len(chunks)


def ensure_schema_updates(db: Session):
    db.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS slug VARCHAR(255)"))
    db.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS intro TEXT"))
    db.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS website_url VARCHAR(500)"))
    db.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS business_description TEXT"))
    db.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS business_logo_url VARCHAR(1000)"))
    db.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS welcome_message TEXT"))

    db.execute(text("""
        UPDATE clients
        SET slug = regexp_replace(lower(name), '[^a-z0-9]+', '-', 'g')
        WHERE slug IS NULL OR slug = ''
    """))

    db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_slug_unique ON clients(slug)"))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS otp_codes (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            code VARCHAR(10) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            consumed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_otp_email_consumed ON otp_codes(email, consumed)"))
    db.commit()


def seed_data():
    """Seed initial testing data"""
    db = next(get_db())
    try:
        # Remove any existing shared/business logins so each business
        # must sign up and receive its own `Client`/`client_id`.
        try:
            deleted = db.query(User).filter(User.role == "business").delete(synchronize_session=False)
            if deleted:
                logger.info("Removed %s existing business user(s) during seed.", deleted)
            db.commit()
        except Exception:
            db.rollback()

        # (Optional) ensure a test client exists for local regular-user testing
        test_client = db.query(Client).filter(Client.name == "Test Company").first()
        if not test_client:
            logger.info("Seeding test client...")
            test_client = Client(
                name="Test Company",
                slug="test-company",
                intro="AI assistant for Test Company",
                website_url=None
            )
            db.add(test_client)
            db.commit()
            db.refresh(test_client)

        # Seed Regular User (keep a non-business test user if missing)
        user_email = "user@test.com"
        if not db.query(User).filter(User.email == user_email).first():
            logger.info("Seeding regular user: %s", user_email)
            hashed_pwd = get_password_hash("password123")
            reg_user = User(
                client_id=test_client.id,
                username=user_email,
                email=user_email,
                full_name="Test Regular User",
                hashed_password=hashed_pwd,
                role="user"
            )
            db.add(reg_user)
            
        db.commit()
        logger.info("Seeding completed successfully")
    except Exception as e:
        logger.exception("Error seeding data: %s", e)
        db.rollback()
    finally:
        db.close()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and seed data on startup"""
    try:
        init_db()
        db = next(get_db())
        try:
            ensure_schema_updates(db)
        finally:
            db.close()
        seed_data()
        logger.info("Database initialized and seeded successfully")
    except Exception as e:
        logger.exception("Error during startup: %s", e)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "chatbot-api"}

# ==================== AUTH ROUTER ====================
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

@auth_router.post("/register", response_model=dict)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and return token (Frontend expectation)"""
    try:
        # Always create a new Client for business signups so no shared
        # or pre-existing business login can be reused.
        client_id = user.client_id
        if user.role == 'business':
            client_name = f"{user.full_name or user.email}'s Org"
            # Avoid name conflicts
            suffix = 1
            original_name = client_name
            while db.query(Client).filter(Client.name == client_name).first():
                client_name = f"{original_name} {suffix}"
                suffix += 1

            new_client = Client(
                name=client_name,
                slug=unique_slug(db, client_name),
                intro=f"AI assistant for {client_name}",
                website_url=None
            )
            db.add(new_client)
            db.commit()
            db.refresh(new_client)
            client_id = new_client.id
        else:
            # If non-business and no client_id provided, create a new client
            if not client_id or client_id == 0:
                client_name = f"{user.full_name or user.email}'s Org"
                suffix = 1
                original_name = client_name
                while db.query(Client).filter(Client.name == client_name).first():
                    client_name = f"{original_name} {suffix}"
                    suffix += 1

                new_client = Client(
                    name=client_name,
                    slug=unique_slug(db, client_name),
                    intro=f"AI assistant for {client_name}",
                    website_url=None
                )
                db.add(new_client)
                db.commit()
                db.refresh(new_client)
                client_id = new_client.id
            else:
                # Verify client exists
                client = db.query(Client).filter(Client.id == client_id).first()
                if not client:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Client with ID {client_id} not found"
                    )
        
        # Use email as username if not provided
        username = user.username or user.email
        
        # Check if username or email already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == user.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email/username already exists"
            )
        
        # Create user
        hashed_password = get_password_hash(user.password)
        db_user = User(
            client_id=client_id,
            username=username,
            email=user.email,
            full_name=user.full_name,
            hashed_password=hashed_password,
            role=user.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Create tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": db_user.username,
                "client_id": db_user.client_id,
                "role": db_user.role
            },
            expires_delta=access_token_expires
        )

        refresh_token = create_refresh_token(
            data={
                "sub": db_user.username,
                "client_id": db_user.client_id,
                "role": db_user.role
            }
        )

        # Return what frontend expects
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "full_name": db_user.full_name,
                "role": db_user.role,
                "client_id": db_user.client_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {str(e)}"
        )

@auth_router.post("/login", response_model=dict)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and return token (Frontend expectation - handles form data)"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "client_id": user.client_id,
            "role": user.role
        },
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data={
            "sub": user.username,
            "client_id": user.client_id,
            "role": user.role
        }
    )

    # Return what frontend expects
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "client_id": user.client_id
        }
    }

@auth_router.post("/refresh", response_model=dict)
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    """Exchange a refresh token for a new access token.

    Expected JSON body: { "refresh_token": "..." }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    refresh = body.get("refresh_token")
    if not refresh:
        raise HTTPException(status_code=400, detail="refresh_token required")

    payload = verify_refresh_token(refresh)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    username = payload.get("sub")
    client_id = payload.get("client_id")
    role = payload.get("role")

    if not username or client_id is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    # Ensure user still exists
    try:
        db_user = db.query(User).filter(
            User.username == username,
            User.client_id == client_id
        ).first()
    except Exception:
        db.close()
        raise HTTPException(status_code=500, detail="Database error")

    if not db_user:
        db.close()
        raise HTTPException(status_code=401, detail="User not found")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": db_user.username,
            "client_id": db_user.client_id,
            "role": db_user.role
        },
        expires_delta=access_token_expires
    )

    # Optionally rotate refresh token
    new_refresh = create_refresh_token(
        data={
            "sub": db_user.username,
            "client_id": db_user.client_id,
            "role": db_user.role
        }
    )

    db.close()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }


@auth_router.post("/otp/request", response_model=dict)
async def request_otp(payload: OtpRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    code = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    db.query(OtpCode).filter(
        OtpCode.email == email,
        OtpCode.consumed == False
    ).update({"consumed": True})

    otp = OtpCode(email=email, code=code, expires_at=expires_at, consumed=False)
    db.add(otp)
    db.commit()

    # In production we don't return the OTP in responses; for local testing
    # it's useful to expose it when DEBUG is enabled via env var.
    debug_enabled = os.getenv('DEBUG', 'False').lower() in ('1', 'true', 'yes')
    resp = {
        "message": "OTP generated. Integrate SMS/Email provider for production delivery. OTP not returned in responses in production.",
    }

    # Log OTP to application logs for operators (safe in dev)
    try:
        logger.info("OTP generated for %s (expires %s)", email, expires_at.isoformat())
    except Exception:
        pass

    if debug_enabled:
        # Expose OTP in API response only when DEBUG is enabled
        resp["debug_otp"] = code

    return resp


@auth_router.post("/otp/verify", response_model=dict)
async def verify_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    otp = db.query(OtpCode).filter(
        OtpCode.email == email,
        OtpCode.code == payload.code,
        OtpCode.consumed == False,
        OtpCode.expires_at > datetime.now(timezone.utc)
    ).order_by(desc(OtpCode.created_at)).first()

    if not otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    otp.consumed = True

    user = db.query(User).filter(User.email == email, User.role == "business").first()

    if not user:
        proposed_name = (payload.full_name or email.split("@")[0]).strip()
        business_name = f"{proposed_name} Business"
        original_name = business_name
        counter = 1
        while db.query(Client).filter(Client.name == business_name).first():
            counter += 1
            business_name = f"{original_name} {counter}"

        client = Client(
            name=business_name,
            slug=unique_slug(db, business_name),
            intro=f"AI assistant for {business_name}",
            website_url=None
        )
        db.add(client)
        db.flush()

        user = User(
            client_id=client.id,
            username=email,
            email=email,
            full_name=payload.full_name or email,
            hashed_password=get_password_hash(str(uuid.uuid4())),
            role="business"
        )
        db.add(user)
        db.flush()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "client_id": user.client_id, "role": user.role},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "client_id": user.client_id, "role": user.role}
    )

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "client_id": user.client_id
        }
    }

app.include_router(auth_router)

# ==================== CLIENT ENDPOINTS ====================

@app.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED, tags=["Clients"])
async def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    """Create a new client (tenant)"""
    try:
        # Check if client already exists
        existing_client = db.query(Client).filter(Client.name == client.name).first()
        if existing_client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client with this name already exists"
            )
        
        db_client = Client(
            name=client.name,
            api_key=client.api_key,
            slug=unique_slug(db, client.name),
            intro=f"AI assistant for {client.name}",
            website_url=None
        )
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        return db_client
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating client: {str(e)}"
        )

# ==================== USER INFO ====================

@app.get("/users/me", response_model=UserResponse, tags=["Users"])
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@app.get("/owner/profile", response_model=BusinessDetail, tags=["Owner"])
async def get_owner_profile(
    current_user: User = Depends(require_business_role),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.client_id, Client.is_active == True).first()
    if not client:
        raise HTTPException(status_code=404, detail="Business not found")
    # Normalize fields for frontend consolidation
    try:
        client.business_name = getattr(client, 'name', None)
        if not getattr(client, 'business_description', None):
            client.business_description = getattr(client, 'intro', None)
    except Exception:
        pass
    return client


@app.put("/owner/profile", response_model=BusinessDetail, tags=["Owner"])
async def upsert_owner_profile(
    payload: OwnerProfileUpsert,
    current_user: User = Depends(require_business_role),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Business not found")

    name_changed = client.name != payload.business_name
    client.name = payload.business_name
    if name_changed:
        client.slug = unique_slug(db, payload.business_name, exclude_client_id=client.id)
    client.intro = payload.intro
    client.website_url = payload.website_url
    # New profile fields
    client.business_description = payload.business_description
    client.welcome_message = payload.welcome_message

    if payload.website_url:
        ingest_website_kb(db, current_user.client_id, payload.website_url)

    db.commit()
    db.refresh(client)
    try:
        client.business_name = getattr(client, 'name', None)
        if not getattr(client, 'business_description', None):
            client.business_description = getattr(client, 'intro', None)
    except Exception:
        pass
    return client


# Public API for current business profile (v1)
@app.get("/api/v1/business/profile", response_model=BusinessDetail, tags=["Business"])
async def get_business_profile(current_user: User = Depends(require_business_role), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == current_user.client_id, Client.is_active == True).first()
    if not client:
        raise HTTPException(status_code=404, detail="Business not found")
    try:
        client.business_name = getattr(client, 'name', None)
        if not getattr(client, 'business_description', None):
            client.business_description = getattr(client, 'intro', None)
    except Exception:
        pass
    return client


# Upload logo and persist path on the client record
@app.post("/api/v1/business/upload-logo", response_model=dict, tags=["Business"])
async def upload_business_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(require_business_role),
    db: Session = Depends(get_db)
):
    # Accept common image types
    allowed = {"png", "jpg", "jpeg", "svg", "webp"}
    ext = (file.filename or "").rsplit('.', 1)[-1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Only images (png,jpg,jpeg,svg,webp) are supported")

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    save_path = os.path.join(LOGO_DIR, unique_filename)
    try:
        with open(save_path, "wb") as fh:
            shutil.copyfileobj(file.file, fh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed saving logo: {e}")

    # Store the public URL path (served by /api/v1/business/logo)
    public_path = f"/static/logos/{unique_filename}"

    client = db.query(Client).filter(Client.id == current_user.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Business not found")

    client.business_logo_url = public_path
    db.commit()
    db.refresh(client)

    return {"logo_url": public_path}


# Serve current business logo file (if uploaded)
@app.get("/api/v1/business/logo", response_class=FileResponse, tags=["Business"])
async def serve_business_logo(current_user: User = Depends(require_business_role), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == current_user.client_id).first()
    if not client or not client.business_logo_url:
        raise HTTPException(status_code=404, detail="Logo not found")

    filename = os.path.basename(client.business_logo_url)
    file_path = os.path.join(LOGO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Logo file not found on server")

    return FileResponse(file_path)


@app.get("/owner/analytics", response_model=OwnerAnalyticsResponse, tags=["Owner"])
async def owner_analytics(
    current_user: User = Depends(require_business_role),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200)
):
    total_questions = db.query(func.count(ChatLog.id)).filter(
        ChatLog.client_id == current_user.client_id
    ).scalar() or 0

    recent_logs = db.query(ChatLog).filter(
        ChatLog.client_id == current_user.client_id
    ).order_by(desc(ChatLog.created_at)).limit(limit).all()

    return OwnerAnalyticsResponse(
        total_questions=total_questions,
        recent_qa=[
            OwnerAnalyticsItem(
                id=log.id,
                session_id=log.session_id,
                question=log.user_message,
                answer=log.bot_response,
                created_at=log.created_at
            )
            for log in recent_logs
        ]
    )


@app.get("/public/businesses", response_model=BusinessListResponse, tags=["Public"])
async def list_public_businesses(
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Client).filter(Client.is_active == True)
    if q:
        search = f"%{q.strip()}%"
        query = query.filter((Client.name.ilike(search)) | (Client.slug.ilike(search)))

    businesses = query.order_by(Client.name.asc()).all()
    payload = [
        BusinessSummary(id=c.id, name=c.name, slug=c.slug, intro=c.intro)
        for c in businesses
    ]
    return BusinessListResponse(businesses=payload, total=len(payload))


@app.get("/public/search", response_model=BusinessListResponse, tags=["Public"])
async def search_public_businesses(q: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    """Search public businesses by name or description. Returns BusinessSummary-like payload."""
    if not q or not q.strip() or len(q.strip()) < 2:
        return BusinessListResponse(businesses=[], total=0)

    search = f"%{q.strip()}%"
    query = db.query(Client).filter(Client.is_active == True).filter(
        or_(
            Client.name.ilike(search),
            Client.business_description.ilike(search),
            Client.intro.ilike(search),
            Client.slug.ilike(search)
        )
    ).order_by(Client.name.asc()).limit(limit)

    businesses = query.all()
    payload = [
        BusinessSummary(
            id=c.id,
            name=c.name,
            slug=c.slug,
            intro=(c.business_description or c.intro or c.welcome_message or '')
        )
        for c in businesses
    ]
    return BusinessListResponse(businesses=payload, total=len(payload))


@app.get("/public/business/{slug}", response_model=BusinessDetail, tags=["Public"])
async def get_public_business(slug: str, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.slug == slug, Client.is_active == True).first()
    if not client:
        raise HTTPException(status_code=404, detail="Business not found")
    try:
        client.business_name = getattr(client, 'name', None)
        if not getattr(client, 'business_description', None):
            client.business_description = getattr(client, 'intro', None)
    except Exception:
        pass
    return client

# ==================== DOCUMENT ROUTER ====================
doc_router = APIRouter(prefix="/documents", tags=["Documents"])

@doc_router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_business_role),
    db: Session = Depends(get_db)
):
    """Upload and process a document (PDF, TXT, or DOCX)"""
    try:
        # Validate file type
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in ['pdf', 'txt', 'docx']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF, TXT, and DOCX files are supported"
            )
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Queue background task for processing (use absolute path)
        abs_file_path = os.path.abspath(file_path)

        # Record enqueue audit row (persist host association reliably)
        try:
            from models import EnqueueAudit
            audit = EnqueueAudit(
                client_id=current_user.client_id,
                filename=file.filename,
                file_path=abs_file_path,
                status="enqueued"
            )
            db.add(audit)
            db.commit()
            db.refresh(audit)
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            audit = None
        # Debug: log client association at enqueue time
        try:
            logger.info("ENQUEUE: Upload saved. enqueue file=%s, original_filename=%s, client_id=%s", abs_file_path, file.filename, current_user.client_id)
        except Exception:
            pass
        try:
            # write an enqueue record to a host-visible log in the uploads folder (kept for ops)
            with open(os.path.join(UPLOAD_DIR, 'api_enqueue.log'), 'a', encoding='utf-8') as fh:
                fh.write(f"{datetime.utcnow().isoformat()} - ENQUEUE file={abs_file_path} original_filename={file.filename} client_id={current_user.client_id}\n")
        except Exception:
            logger.debug("Failed to write enqueue log")
        try:
            task = process_document.delay(
                file_path=abs_file_path,
                filename=file.filename,
                file_type=file_extension,
                client_id=current_user.client_id
            )

            try:
                task_id = getattr(task, 'id', None)
                logger.info(
                    "Enqueued processing task id=%s for client_id=%s file=%s",
                    task_id,
                    current_user.client_id,
                    file.filename,
                )
                # persist task id back to audit row if present
                if audit and task_id:
                    audit.task_id = task_id
                    db.add(audit)
                    db.commit()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass

            try:
                # also write the celery task id to the host-visible enqueue log
                with open(os.path.join(UPLOAD_DIR, 'api_enqueue.log'), 'a', encoding='utf-8') as fh:
                    fh.write(
                        f"{datetime.utcnow().isoformat()} - TASK id={getattr(task, 'id', None)} file={abs_file_path} original_filename={file.filename} client_id={current_user.client_id}\n"
                    )
            except Exception:
                logger.debug("Failed to write task id to enqueue log")
        except Exception as e:
            # If Celery/Redis not available, fallback to synchronous processing
            logger.warning("Celery enqueue failed, processing inline: %s", e)
            try:
                func = getattr(process_document, '__wrapped__', None)
                if func is None:
                    # Last resort: call task directly (may be a bound task)
                    process_document(None, abs_file_path, file.filename, file_extension, current_user.client_id)
                else:
                    # If wrapped is a bound method, call without explicit self
                    if hasattr(func, '__self__') and func.__self__ is not None:
                        func(abs_file_path, file.filename, file_extension, current_user.client_id)
                    else:
                        func(None, abs_file_path, file.filename, file_extension, current_user.client_id)
            except Exception as ie:
                logger.exception('Inline processing failed: %s', ie)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Processing failed: {str(ie)}"
                )
        
        return DocumentUploadResponse(
            filename=file.filename,
            file_type=file_extension,
            total_chunks=0,
            message=f"File uploaded successfully. Processing in background."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )

@doc_router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(require_business_role),
    db: Session = Depends(get_db)
):
    """List all documents for the current client (Frontend expectation format)"""
    try:
        # Get unique documents with count and date
        docs = db.query(
            func.min(Document.id).label('id'),
            Document.filename,
            Document.file_type,
            func.count(Document.id).label('chunk_count'),
            func.max(Document.created_at).label('created_at')
        ).filter(
            Document.client_id == current_user.client_id
        ).group_by(
            Document.filename,
            Document.file_type
        ).all()
        
        doc_list = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "chunk_count": doc.chunk_count,
                "status": "completed",
                "created_at": doc.created_at
            }
            for doc in docs
        ]
        
        return DocumentListResponse(
            documents=doc_list,
            total=len(doc_list)
        )
    except Exception as e:
        logger.exception("Error listing documents: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing documents: {str(e)}"
        )

@doc_router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    current_user: User = Depends(require_business_role),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.client_id == current_user.client_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db.query(Document).filter(
        Document.client_id == current_user.client_id,
        Document.filename == doc.filename
    ).delete(synchronize_session=False)
    db.commit()
    return JSONResponse(content={"message": "Document deleted"}, status_code=200)


@doc_router.post("/refresh-url", response_model=dict)
async def refresh_website_kb(
    website_url: str = Query(..., min_length=5),
    current_user: User = Depends(require_business_role),
    db: Session = Depends(get_db)
):
    try:
        chunk_count = ingest_website_kb(db, current_user.client_id, website_url)

        owner_client = db.query(Client).filter(Client.id == current_user.client_id).first()
        if owner_client:
            owner_client.website_url = website_url

        db.commit()
        return {"message": "Website knowledge base refreshed", "chunks": chunk_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to refresh URL KB: {str(e)}")

app.include_router(doc_router)

#--------------------------------------------------------------------------

def retrieve_context_chunks(db, query_embedding, client_id, top_k=5):

    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    sql = text("""
        SELECT chunk_text
        FROM documents
        WHERE client_id = :client_id
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """)

    result = db.execute(
        sql,
        {
            "embedding": embedding_str,
            "client_id": client_id,
            "top_k": top_k
        }
    ).fetchall()

    chunks = [row[0] for row in result]

    logger.debug("Context retrieval: embedding_len=%s client_id=%s chunks_returned=%s", len(query_embedding), client_id, len(chunks))
    if chunks:
        logger.debug("First chunk preview: %s", (chunks[0][:100] if chunks[0] else "Empty"))

    return chunks


# ==================== CHAT ENDPOINTS ====================

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Chat endpoint supporting both authenticated and guest users"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        user_email = current_user.email if current_user else "Guest"
        client_id = current_user.client_id if current_user else 1 # Default to Client 1 for guests
        user_id = current_user.id if current_user else None
        
        logger.debug("Chat request started. User: %s, Session: %s, Client: %s", user_email, session_id, client_id)
        
        # Get chat history (without trying to fetch embeddings)
        try:
            query = db.query(ChatLog).filter(
                ChatLog.client_id == client_id,
                ChatLog.session_id == session_id
            )
            
            if user_id:
                query = query.filter(ChatLog.user_id == user_id)
            else:
                query = query.filter(ChatLog.user_id == None)
                
            recent_history = query.order_by(desc(ChatLog.created_at)).limit(10).all()
            logger.debug("Fetched history. Count: %s", len(recent_history))
        except Exception as he:
            logger.debug("History fetch error: %s", he)
            db.rollback()
            recent_history = []
        
        chat_history = [
            {"user": log.user_message, "assistant": log.bot_response}
            for log in reversed(recent_history)
        ]
        
        # Generate response without RAG context
        # If mock mode is enabled, skip embedding/RAG calls to avoid external API calls
        if os.getenv("MOCK_GEMINI", "false").lower() in ("1", "true", "yes"):
            context_chunks = []
        else:
            # Generate embedding for query
            try:
                logger.debug("Generating embedding for chat request")
                query_embedding = gemini_service.generate_query_embedding(request.message)

                logger.debug("Retrieving context chunks for client %s", client_id)
                context_chunks = retrieve_context_chunks(
                    db,
                    query_embedding,
                    client_id,
                    top_k=5
                )
                logger.debug("Context chunks retrieved: %s", len(context_chunks))
            except Exception as e:
                logger.warning("Embedding/RAG failure: %s", e)
                db.rollback() # Clear aborted transaction state
                context_chunks = []


        # Generate grounded response
        logger.debug("Preparing response for chat request")

        # If there are no context chunks, enforce KB-only behavior:
        # reply exactly with the required refusal message and skip calling Gemini.
        if not context_chunks:
            gemini_response = {
                'response': "I don't have that information in the provided documents.",
                'tokens_used': 0
            }
            logger.debug("No context found — returning KB-only refusal message.")
        else:
            logger.debug("Calling Gemini service for chat response")
            try:
                gemini_response = gemini_service.generate_chat_response(
                    user_message=request.message,
                    context=context_chunks,
                    chat_history=chat_history if chat_history else None
                )
                logger.debug("Gemini response received. Success: %s", bool(gemini_response))
            except Exception as ge:
                logger.warning("Gemini service CRASHED: %s", ge)
                logger.exception(ge)
                raise
        
        # Log the chat interaction
        logger.debug("Logging chat to database")
        try:
            chat_log = ChatLog(
                client_id=client_id,
                user_id=user_id,
                session_id=session_id,
                user_message=request.message,
                bot_response=gemini_response['response'],
                context_used="\n".join(context_chunks) if context_chunks else None,
                tokens_used=gemini_response.get('tokens_used')
            )
            db.add(chat_log)
            db.commit()
            logger.debug("Chat logged successfully.")
        except Exception as le:
            logger.warning("Logging error: %s", le)
            db.rollback()
            # We don't raise here, we want the user to get the response even if logging fails
        
        return ChatResponse(
            response=gemini_response['response'],
            session_id=session_id,
            context_used=None
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Chat error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )

@app.get("/chat/history", response_model=ChatHistoryResponse, tags=["Chat"])
async def get_chat_history(
    session_id: Optional[str] = Query(None),
    current_user: User = Depends(require_any_role),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get chat history for current user"""
    try:
        query = db.query(ChatLog).filter(
            ChatLog.client_id == current_user.client_id,
            ChatLog.user_id == current_user.id
        )
        
        if session_id:
            query = query.filter(ChatLog.session_id == session_id)
        
        query = query.order_by(desc(ChatLog.created_at))
        
        total = query.count()
        history = query.offset(skip).limit(limit).all()
        
        return ChatHistoryResponse(
            history=[ChatHistoryItem.from_orm(log) for log in history],
            total=total
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat history: {str(e)}"
        )

# ==================== ERROR HANDLERS ====================

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.warning("Validation Error: %s", exc.errors())
    logger.debug("Request body: %s", exc.body)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

@app.post("/public/business/{slug}/chat", response_model=ChatResponse, tags=["Public Chat"])
async def public_business_chat(
    slug: str,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    try:
        client = db.query(Client).filter(Client.slug == slug, Client.is_active == True).first()
        if not client:
            raise HTTPException(status_code=404, detail="Business not found")

        session_id = request.session_id or str(uuid.uuid4())

        try:
            query_embedding = gemini_service.generate_query_embedding(request.message)
            context_chunks = retrieve_context_chunks(db, query_embedding, client.id, top_k=5)
        except Exception as e:
            logger.warning("Embedding/RAG failure: %s", e)
            db.rollback()
            context_chunks = []

        if not context_chunks:
            gemini_response = {
                'response': "I don't have that information in the provided documents.",
                'tokens_used': 0
            }
        else:
            gemini_response = gemini_service.generate_chat_response(
                user_message=request.message,
                context=context_chunks,
                chat_history=None
            )

        db.add(ChatLog(
            client_id=client.id,
            user_id=None,
            session_id=session_id,
            user_message=request.message,
            bot_response=gemini_response["response"],
            context_used="\n".join(context_chunks) if context_chunks else None,
            tokens_used=gemini_response.get("tokens_used")
        ))
        db.commit()

        return ChatResponse(
            response=gemini_response["response"],
            session_id=session_id,
            context_used=None
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/public/chat", response_model=ChatResponse, tags=["Public Chat"])
async def public_chat_legacy(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    if not request.tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id required")

    client = db.query(Client).filter(Client.id == request.tenant_id, Client.is_active == True).first()
    if not client:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return await public_business_chat(client.slug, request, db)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
