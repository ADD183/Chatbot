# Developer Quick Reference

## 🚀 Quick Start Commands

### First Time Setup
```bash
# 1. Clone and navigate
cd chatbot

# 2. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 3. Start all services
docker-compose up -d

# 4. Check health
curl http://localhost:8000/health

# 5. View API docs
# Open browser: http://localhost:8000/docs
```

### Daily Development
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Stop services
docker-compose down

# Restart a service
docker-compose restart api

# Rebuild after code changes
docker-compose up -d --build
```

## 📝 Common Tasks

### Create a Test Client and User
```bash
# Create client
curl -X POST http://localhost:8000/clients \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Client"}'

# Create business user
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "SecurePass123!",
    "role": "business",
    "client_id": 1
  }'

# Login
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "SecurePass123!"}'
```

### Upload and Test RAG
```bash
# Save token from login
TOKEN="your-jwt-token-here"

# Upload a document
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf"

# Wait 10 seconds for processing, then chat
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the key points in the document?"}'
```

## 🗄️ Database Commands

### Access PostgreSQL
```bash
# Connect to database
docker-compose exec postgres psql -U chatbot_user -d chatbot_db

# List tables
\dt

# View table schema
\d documents

# Query data
SELECT client_id, filename, COUNT(*) as chunks 
FROM documents 
GROUP BY client_id, filename;

# Exit
\q
```

### Database Maintenance
```bash
# Backup database
docker-compose exec postgres pg_dump -U chatbot_user chatbot_db > backup.sql

# Restore database
docker-compose exec -T postgres psql -U chatbot_user chatbot_db < backup.sql

# Vacuum and analyze
docker-compose exec postgres psql -U chatbot_user -d chatbot_db -c "VACUUM ANALYZE;"
```

## 🔧 Redis Commands

### Access Redis
```bash
# Connect to Redis
docker-compose exec redis redis-cli

# View all keys
KEYS *

# Check queue length
LLEN celery

# View task info
GET celery-task-meta-<task-id>

# Clear all data (careful!)
FLUSHALL

# Exit
exit
```

## 🐛 Debugging

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 api
```

### Check Service Status
```bash
# List all containers
docker-compose ps

# Check resource usage
docker stats

# Inspect a container
docker-compose exec api env
```

### Common Issues

**Issue: Database connection error**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

**Issue: Celery tasks not processing**
```bash
# Check worker logs
docker-compose logs worker

# Check Redis connection
docker-compose exec redis redis-cli ping

# Restart worker
docker-compose restart worker
```

**Issue: pgvector extension not found**
```bash
# Enable extension manually
docker-compose exec postgres psql -U chatbot_user -d chatbot_db -c "CREATE EXTENSION vector;"
```

## 🧪 Testing

### Run Test Suite
```bash
# Install requests library
pip install requests

# Run tests
python test_api.py
```

### Manual API Testing
```bash
# Import Postman collection
# File: postman_collection.json
# Import into Postman and run the collection
```

### Test Individual Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Get API documentation
curl http://localhost:8000/openapi.json
```

## 📊 Monitoring

### Check Application Health
```bash
# API health
curl http://localhost:8000/health

# Database health
docker-compose exec postgres pg_isready -U chatbot_user

# Redis health
docker-compose exec redis redis-cli ping
```

### Monitor Celery Tasks
```bash
# View active tasks
docker-compose exec worker celery -A worker.celery_app inspect active

# View registered tasks
docker-compose exec worker celery -A worker.celery_app inspect registered

# View worker stats
docker-compose exec worker celery -A worker.celery_app inspect stats
```

## 🔐 Security

### Generate Secret Key
```python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Hash a Password
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(pwd_context.hash("your-password"))
```

### Decode JWT Token
```python
from jose import jwt
token = "your-jwt-token"
secret = "your-secret-key"
print(jwt.decode(token, secret, algorithms=["HS256"]))
```

## 📁 File Locations

### Configuration
- Environment: `.env`
- Docker: `docker-compose.yml`
- Database init: `init.sql`

### Source Code
- API: `main.py`
- Models: `models.py`
- Schemas: `schemas.py`
- Auth: `auth.py`
- Gemini: `gemini_service.py`
- Worker: `worker.py`
- Database: `database.py`

### Documentation
- User guide: `README.md`
- Architecture: `ARCHITECTURE.md`
- Deployment: `DEPLOYMENT.md`
- Summary: `PROJECT_SUMMARY.md`

### Testing
- Test suite: `test_api.py`
- Postman: `postman_collection.json`

## 🎯 Code Patterns

### Adding a New Endpoint
```python
# In main.py
@app.post("/new-endpoint", response_model=ResponseSchema, tags=["Category"])
async def new_endpoint(
    request: RequestSchema,
    current_user: User = Depends(require_business_role),
    db: Session = Depends(get_db)
):
    """Endpoint description"""
    try:
        # Validate multi-tenancy
        result = db.query(Model).filter(
            Model.client_id == current_user.client_id
        ).all()
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )
```

### Adding a New Model
```python
# In models.py
class NewModel(Base):
    __tablename__ = "new_table"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    # ... other fields
    
    client = relationship("Client", back_populates="new_models")
    
    __table_args__ = (
        Index('idx_new_model_client', 'client_id'),
    )

# In Client model, add:
new_models = relationship("NewModel", back_populates="client")
```

### Adding a Celery Task
```python
# In worker.py
@celery_app.task(bind=True, max_retries=3)
def new_task(self, param1, param2):
    """Task description"""
    db = SessionLocal()
    try:
        # Task logic
        result = process_data(param1, param2)
        db.commit()
        return {"status": "success", "result": result}
    except Exception as e:
        db.rollback()
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()
```

## 🔄 Update Workflow

### Update Dependencies
```bash
# Update requirements.txt
pip install --upgrade package-name
pip freeze > requirements.txt

# Rebuild containers
docker-compose up -d --build
```

### Database Migration
```bash
# Install Alembic (already in requirements.txt)
docker-compose exec api alembic init alembic

# Create migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply migration
docker-compose exec api alembic upgrade head
```

### Code Changes
```bash
# 1. Make changes to Python files
# 2. Rebuild and restart
docker-compose up -d --build

# 3. Check logs for errors
docker-compose logs -f api
```

## 📈 Performance Tuning

### Increase Workers
```yaml
# In docker-compose.yml
worker:
  command: celery -A worker.celery_app worker --loglevel=info --concurrency=8
```

### Increase API Instances
```bash
# Scale API service
docker-compose up -d --scale api=3
```

### Database Connection Pool
```python
# In database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,      # Increase
    max_overflow=40,   # Increase
)
```

## 🌐 Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | 30 |
| `ENVIRONMENT` | Environment name | development |
| `DEBUG` | Debug mode | True |

## 🎓 Learning Path

1. **Start Here**: `README.md`
2. **Understand Architecture**: `ARCHITECTURE.md`
3. **Run Tests**: `test_api.py`
4. **Explore API**: http://localhost:8000/docs
5. **Read Code**: Start with `main.py`, then `models.py`
6. **Deploy**: `DEPLOYMENT.md`

## 💡 Tips & Tricks

### Fast Iteration
```bash
# Use --build only when dependencies change
docker-compose up -d

# For code changes, just restart
docker-compose restart api
```

### Debug Mode
```python
# In main.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Quick Database Reset
```bash
docker-compose down -v  # Removes volumes
docker-compose up -d    # Fresh start
```

### Export/Import Data
```bash
# Export
docker-compose exec postgres pg_dump -U chatbot_user chatbot_db -t documents > documents.sql

# Import
docker-compose exec -T postgres psql -U chatbot_user chatbot_db < documents.sql
```

---

**Need Help?** Check the documentation files or open an issue!
