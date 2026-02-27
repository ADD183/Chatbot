# Multi-Tenant AI Chatbot Backend

A production-ready FastAPI backend for a multi-tenant AI chatbot system using Google Gemini API and PostgreSQL with pgvector for RAG (Retrieval-Augmented Generation).

## Features

- **Multi-Tenancy**: Complete data isolation per client with `client_id` filtering
- **Role-Based Access Control (RBAC)**: 
  - `business` role: Full access to upload, files, and chat
  - `user` role: Chat-only access
- **RAG Implementation**: 
  - PDF/TXT document parsing and chunking
  - Vector embeddings using Google Gemini `text-embedding-004`
  - Similarity search with pgvector
  - Context-aware responses using `gemini-1.5-flash`
- **Async Processing**: Background document processing with Celery
- **Production-Ready**: Docker orchestration, health checks, error handling

## Tech Stack

- **FastAPI**: Modern Python web framework
- **PostgreSQL + pgvector**: Vector database for embeddings
- **Google Gemini API**: Embeddings and chat generation
- **Celery + Redis**: Background task processing
- **SQLAlchemy**: ORM for database operations
- **JWT**: Secure authentication
- **Docker**: Containerization and orchestration

## Project Structure

```
chatbot/
├── main.py                 # FastAPI application entry point
├── database.py            # Database configuration and pgvector setup
├── models.py              # SQLAlchemy models
├── schemas.py             # Pydantic schemas
├── auth.py                # JWT authentication and RBAC
├── gemini_service.py      # Google Gemini API integration
├── worker.py              # Celery tasks for document processing
├── requirements.txt       # Python dependencies
├── Dockerfile             # Multi-stage Docker build
├── docker-compose.yml     # Service orchestration
├── init.sql               # PostgreSQL initialization
└── .env.example           # Environment variables template
```

## Setup Instructions

### 1. Prerequisites

- Docker and Docker Compose
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### 2. Environment Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your-actual-gemini-api-key-here
SECRET_KEY=your-secure-secret-key-for-jwt
```

Windows (PowerShell) example:

```powershell
copy .env.example .env
$env:GEMINI_API_KEY = 'your-actual-gemini-api-key-here'
$env:SECRET_KEY = 'your-secure-secret-key-for-jwt'
```

Windows (cmd.exe) example:

```cmd
copy .env.example .env
set GEMINI_API_KEY=your-actual-gemini-api-key-here
set SECRET_KEY=your-secure-secret-key-for-jwt
```

### 3. Start the Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL with pgvector (port 5432)
- Redis (port 6379)
- FastAPI API (port 8000)
- Celery Worker
- Celery Beat (for scheduled tasks)

### 4. Verify Installation

Check service health:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "service": "chatbot-api"}
```

## API Usage

### 1. Create a Client (Tenant)

```bash
curl -X POST http://localhost:8000/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp"
  }'
```

Response:
```json
{
  "id": 1,
  "name": "Acme Corp",
  "is_active": true,
  "created_at": "2026-02-10T00:00:00Z"
}
```

### 2. Create a User

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_business",
    "email": "john@acme.com",
    "password": "securepass123",
    "role": "business",
    "client_id": 1
  }'
```

### 3. Login

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_business",
    "password": "securepass123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 4. Upload a Document (Business Role Only)

```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

Response:
```json
{
  "filename": "document.pdf",
  "file_type": "pdf",
  "total_chunks": 0,
  "message": "File uploaded successfully. Processing in background. Task ID: abc-123"
}
```

### 5. List Documents (Business Role Only)

```bash
curl -X GET http://localhost:8000/files \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. Chat with RAG

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the key points in the uploaded documents?"
  }'
```

Response:
```json
{
  "response": "Based on the provided context, the key points are...",
  "session_id": "uuid-here",
  "context_used": ["chunk1", "chunk2"]
}
```

### 7. Get Chat History

```bash
curl -X GET "http://localhost:8000/chat/history?session_id=SESSION_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Multi-Tenancy Implementation

Every database query is automatically filtered by `client_id`:

```python
# Example from chat endpoint
similar_docs = db.query(Document).filter(
    Document.client_id == current_user.client_id  # ← Multi-tenancy enforcement
).order_by(...)
```

This ensures complete data isolation between clients.

## RBAC Implementation

Role-based access is enforced using FastAPI dependencies:

```python
# Business role required
@app.post("/upload")
async def upload_document(
    current_user: User = Depends(require_business_role)  # ← RBAC check
):
    ...

# Any authenticated user
@app.post("/chat")
async def chat(
    current_user: User = Depends(require_any_role)  # ← RBAC check
):
    ...
```

## RAG Pipeline

1. **Document Upload**: PDF/TXT files are uploaded
2. **Text Extraction**: PyMuPDF extracts text from PDFs
3. **Chunking**: Text is split into ~500 character chunks with 50 char overlap
4. **Embedding**: Each chunk is embedded using Gemini `text-embedding-004`
5. **Storage**: Embeddings stored in PostgreSQL with pgvector
6. **Query**: User questions are embedded and similarity search finds relevant chunks
7. **Context**: Top 5 similar chunks are passed to Gemini with system prompt
8. **Response**: Gemini generates answer using ONLY the provided context

## Database Schema

### Clients Table
- `id`: Primary key
- `name`: Unique client name
- `api_key`: Optional client-specific API key
- `is_active`: Active status
- `created_at`, `updated_at`: Timestamps

### Users Table
- `id`: Primary key
- `client_id`: Foreign key to clients
- `username`: Unique username
- `email`: Unique email
- `hashed_password`: Bcrypt hashed password
- `role`: 'business' or 'user'
- `is_active`: Active status

### Documents Table
- `id`: Primary key
- `client_id`: Foreign key to clients
- `filename`: Original filename
- `file_type`: 'pdf' or 'txt'
- `chunk_text`: Text content of chunk
- `chunk_index`: Position in document
- `embedding`: Vector(768) - pgvector column
- `metadata`: JSON metadata

### ChatLogs Table
- `id`: Primary key
- `client_id`: Foreign key to clients
- `user_id`: Foreign key to users
- `session_id`: Groups related messages
- `user_message`: User's question
- `bot_response`: AI's answer
- `context_used`: Retrieved document chunks
- `tokens_used`: Token count

## Development

### Run Locally Without Docker

1. Install PostgreSQL with pgvector
2. Install Redis
3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Frontend (React / Vite)

Install and run the frontend dev server (from `frontend/`):

```bash
cd frontend
npm install
npm run dev      # starts Vite dev server (default: http://localhost:5173)
npm run build    # build production bundle -> frontend/dist
```

If you prefer Docker for the frontend, build the frontend asset bundle locally then serve it with your preferred static host or include it in your API container.

4. Set environment variables:

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/chatbot_db
export REDIS_URL=redis://localhost:6379/0
export GEMINI_API_KEY=your-key
export SECRET_KEY=your-secret
```

Windows (PowerShell) example:

```powershell
$env:DATABASE_URL = 'postgresql://user:pass@localhost:5432/chatbot_db'
$env:REDIS_URL = 'redis://localhost:6379/0'
$env:GEMINI_API_KEY = 'your-key'
$env:SECRET_KEY = 'your-secret'
```

5. Run migrations:

```bash
python -c "from database import init_db; init_db()"
```

6. Start the API:

```bash
uvicorn main:app --reload
```

7. Start Celery worker:

```bash
celery -A worker.celery_app worker --loglevel=info
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Production Considerations

1. **Security**:
   - Change `SECRET_KEY` to a strong random value
   - Use HTTPS in production
   - Configure CORS appropriately
   - Implement rate limiting

2. **Scaling**:
   - Increase Celery worker concurrency
   - Use connection pooling (already configured)
   - Add caching layer (Redis)
   - Consider read replicas for PostgreSQL

3. **Monitoring**:
   - Add logging (e.g., Sentry)
   - Monitor Celery tasks
   - Track API metrics
   - Set up alerts

4. **Backup**:
   - Regular PostgreSQL backups
   - Document storage backup
   - Configuration backup

## Troubleshooting

### pgvector Extension Not Found

```bash
docker-compose exec postgres psql -U chatbot_user -d chatbot_db -c "CREATE EXTENSION vector;"
```

### Celery Tasks Not Processing

Check worker logs:
```bash
docker-compose logs worker
```

### Database Connection Issues

Verify PostgreSQL is running:
```bash
docker-compose ps postgres
```

## License

MIT License - feel free to use in your projects!

## Support

For issues and questions, please open an issue on GitHub.

## Pushing to GitHub

If you haven't already pushed this repository to GitHub, a typical workflow is:

```bash
git remote add origin https://github.com/<your-user-or-org>/Chatbot.git
git branch -M main
git push -u origin main
```

Make sure to add any production secrets in the GitHub repository settings (Settings → Secrets → Actions).
