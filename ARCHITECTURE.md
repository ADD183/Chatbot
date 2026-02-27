# Architecture Documentation

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  (Web/Mobile Apps, API Clients, Third-party Integrations)      │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/REST
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Auth       │  │   Upload     │  │    Chat      │         │
│  │  Middleware  │  │   Handler    │  │   Handler    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Multi-Tenancy Filter Layer                  │  │
│  │         (client_id enforcement on all queries)           │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────┬──────────────────────┬──────────────────┬─────────────┘
         │                      │                  │
         ▼                      ▼                  ▼
┌─────────────────┐   ┌─────────────────┐   ┌──────────────────┐
│   PostgreSQL    │   │  Redis Queue    │   │  Gemini API      │
│   + pgvector    │   │                 │   │  - Embeddings    │
│                 │   │  ┌───────────┐  │   │  - Chat          │
│  ┌───────────┐  │   │  │  Celery   │  │   └──────────────────┘
│  │  Clients  │  │   │  │  Tasks    │  │
│  │  Users    │  │   │  └─────┬─────┘  │
│  │  Documents│  │   │        │        │
│  │  ChatLogs │  │   └────────┼────────┘
│  └───────────┘  │            │
└─────────────────┘            ▼
                     ┌─────────────────┐
                     │ Celery Workers  │
                     │  - PDF Parser   │
                     │  - Embedder     │
                     │  - Chunker      │
                     └─────────────────┘
```

## Data Flow

### 1. Document Upload Flow

```
User (Business Role)
    │
    ├─→ POST /upload (with JWT token)
    │
    ▼
FastAPI validates:
    ├─ JWT token validity
    ├─ User role = 'business'
    ├─ File type (PDF/TXT)
    └─ Multi-tenancy (client_id from token)
    │
    ├─→ Save file to uploads/
    │
    ├─→ Queue Celery task
    │
    ▼
Celery Worker:
    ├─→ Extract text (PyMuPDF for PDF)
    ├─→ Chunk text (~500 chars, 50 overlap)
    ├─→ For each chunk:
    │   ├─→ Call Gemini API (text-embedding-004)
    │   ├─→ Get 768-dim vector
    │   └─→ Store in PostgreSQL with client_id
    │
    └─→ Return success/failure
```

### 2. Chat Flow (RAG)

```
User (Any Role)
    │
    ├─→ POST /chat {"message": "..."}
    │
    ▼
FastAPI validates:
    ├─ JWT token validity
    ├─ Extract client_id from token
    └─ Multi-tenancy enforcement
    │
    ├─→ Generate query embedding (Gemini)
    │
    ├─→ Similarity search in PostgreSQL:
    │   SELECT chunk_text, embedding <=> query_embedding AS distance
    │   FROM documents
    │   WHERE client_id = ? 
    │   ORDER BY distance
    │   LIMIT 5
    │
    ├─→ Get top 5 relevant chunks (distance < 0.5)
    │
    ├─→ Build prompt:
    │   System: "Answer ONLY using context..."
    │   Context: [chunk1, chunk2, ...]
    │   History: [previous messages]
    │   User: "current question"
    │
    ├─→ Call Gemini API (gemini-1.5-flash)
    │
    ├─→ Store chat log with client_id
    │
    └─→ Return response + context used
```

## Multi-Tenancy Implementation

### Database Level
Every table has `client_id` column with foreign key to `clients` table:

```sql
-- Example: Documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    ...
);

-- Index for fast filtering
CREATE INDEX idx_document_client_filename ON documents(client_id, filename);
```

### Application Level
All queries automatically filter by `client_id`:

```python
# Extracted from JWT token
current_user.client_id

# Applied to every query
db.query(Document).filter(
    Document.client_id == current_user.client_id  # ← Enforced
).all()
```

### Security Guarantees
1. **Token-based**: client_id comes from JWT, not user input
2. **Automatic**: Dependency injection ensures no query bypasses filter
3. **Cascading**: ON DELETE CASCADE ensures clean data removal
4. **Indexed**: Fast queries even with millions of records

## RBAC Implementation

### Role Definitions

| Role     | /upload | /files | /chat | /chat/history |
|----------|---------|--------|-------|---------------|
| business | ✓       | ✓      | ✓     | ✓             |
| user     | ✗       | ✗      | ✓     | ✓             |

### Implementation

```python
# In auth.py
def require_role(allowed_roles: list):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Access denied")
        return current_user
    return role_checker

# Usage in endpoints
@app.post("/upload")
async def upload(current_user: User = Depends(require_role(["business"]))):
    # Only business users can access
    ...

@app.post("/chat")
async def chat(current_user: User = Depends(require_role(["business", "user"]))):
    # Both roles can access
    ...
```

## Vector Search with pgvector

### Embedding Storage

```python
# 768-dimensional vector from Gemini
embedding = gemini_service.generate_embedding(text)

# Store in PostgreSQL
document = Document(
    client_id=client_id,
    chunk_text=text,
    embedding=embedding  # pgvector handles this
)
```

### Similarity Search

```python
# Cosine similarity search
similar_docs = db.query(
    Document.chunk_text,
    Document.embedding.cosine_distance(query_embedding).label('distance')
).filter(
    Document.client_id == client_id  # Multi-tenancy
).order_by('distance').limit(5).all()

# Only use chunks with distance < 0.5 (configurable threshold)
context = [doc.chunk_text for doc in similar_docs if doc.distance < 0.5]
```

### Index Optimization

```python
# IVFFlat index for faster similarity search
Index(
    'idx_document_embedding',
    'embedding',
    postgresql_using='ivfflat',
    postgresql_ops={'embedding': 'vector_cosine_ops'}
)
```

## Error Handling Strategy

### 1. Gemini API Errors
- **Retry Logic**: 3 attempts with exponential backoff
- **Timeout**: 30 seconds per request
- **Fallback**: Graceful error message to user

```python
for attempt in range(self.max_retries):
    try:
        result = genai.embed_content(...)
        return result['embedding']
    except Exception as e:
        if attempt < self.max_retries - 1:
            time.sleep(self.retry_delay * (attempt + 1))
        else:
            raise Exception(f"Failed after {self.max_retries} attempts")
```

### 2. Database Errors
- **Connection Pooling**: Pre-ping to detect stale connections
- **Transaction Management**: Automatic rollback on errors
- **Cascade Deletes**: Clean up related records

### 3. File Processing Errors
- **Validation**: Check file type before processing
- **Celery Retries**: 3 attempts for failed tasks
- **Cleanup**: Remove uploaded files after processing

## Scaling Considerations

### Horizontal Scaling

1. **API Servers**: Stateless, can run multiple instances behind load balancer
2. **Celery Workers**: Add more workers for parallel document processing
3. **Database**: Read replicas for chat queries (writes are less frequent)

### Vertical Scaling

1. **Database**: Increase connection pool size
2. **Worker Concurrency**: Increase Celery worker threads
3. **Vector Index**: Tune IVFFlat parameters for dataset size

### Caching Strategy

1. **Embeddings**: Cache frequently queried embeddings in Redis
2. **User Sessions**: Store JWT validation results
3. **Document Metadata**: Cache file lists per client

## Performance Metrics

### Expected Performance

- **Document Upload**: ~2-5 seconds for 10-page PDF
- **Embedding Generation**: ~100-200ms per chunk
- **Chat Response**: ~1-3 seconds (including similarity search + Gemini)
- **Concurrent Users**: 100+ with single API instance

### Bottlenecks

1. **Gemini API**: Rate limits (check your quota)
2. **Vector Search**: Scales with document count (use IVFFlat index)
3. **Database Connections**: Pool size (default: 10 + 20 overflow)

## Security Best Practices

### Implemented

✓ JWT-based authentication
✓ Password hashing (bcrypt)
✓ Role-based access control
✓ Multi-tenancy data isolation
✓ SQL injection prevention (SQLAlchemy ORM)
✓ File type validation
✓ CORS configuration

### Recommended for Production

- [ ] HTTPS/TLS encryption
- [ ] Rate limiting (e.g., slowapi)
- [ ] API key rotation
- [ ] Audit logging
- [ ] Input sanitization
- [ ] DDoS protection
- [ ] Security headers
- [ ] Regular dependency updates

## Monitoring & Observability

### Recommended Tools

1. **Application Monitoring**: Sentry, New Relic
2. **Database Monitoring**: pgAdmin, DataDog
3. **Celery Monitoring**: Flower
4. **Logging**: ELK Stack, CloudWatch
5. **Metrics**: Prometheus + Grafana

### Key Metrics to Track

- API response times
- Gemini API success/failure rates
- Document processing queue length
- Database query performance
- Token usage and costs
- User activity per tenant

## Backup & Disaster Recovery

### Database Backups

```bash
# Daily automated backups
docker-compose exec postgres pg_dump -U chatbot_user chatbot_db > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgres psql -U chatbot_user chatbot_db < backup_20260210.sql
```

### Document Storage

- Regular backups of `uploads/` directory
- Consider S3 or cloud storage for production
- Implement versioning for critical documents

### Configuration Backups

- Version control for all code
- Encrypted backups of `.env` files
- Document API keys in secure vault (e.g., AWS Secrets Manager)
