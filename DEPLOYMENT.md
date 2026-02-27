# Production Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Google Gemini API key
- Domain name (optional, for HTTPS)
- SSL certificate (optional, for HTTPS)

## Deployment Options

### Option 1: Docker Compose (Recommended for Small-Medium Scale)

#### Step 1: Clone and Configure

```bash
git clone <your-repo>
cd chatbot
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://chatbot_user:STRONG_PASSWORD@postgres:5432/chatbot_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=<generate-strong-random-key>
GEMINI_API_KEY=<your-gemini-api-key>
ENVIRONMENT=production
DEBUG=False
```

Generate a strong secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Step 2: Update docker-compose.yml for Production

```yaml
# Change PostgreSQL password
environment:
  POSTGRES_PASSWORD: <STRONG_PASSWORD>

# Add resource limits
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

#### Step 3: Deploy

```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Step 4: Initialize Database

```bash
# Database is auto-initialized on first run
# Verify tables exist
docker-compose exec postgres psql -U chatbot_user -d chatbot_db -c "\dt"
```

#### Step 5: Create First Client and User

```bash
# Create client
curl -X POST http://localhost:8000/clients \
  -H "Content-Type: application/json" \
  -d '{"name": "Production Client"}'

# Create admin user
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@company.com",
    "password": "SecurePassword123!",
    "role": "business",
    "client_id": 1
  }'
```

### Option 2: Kubernetes (For Large Scale)

#### Step 1: Create Kubernetes Manifests

Create `k8s/` directory with:

**postgres-deployment.yaml**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: ankane/pgvector:latest
        env:
        - name: POSTGRES_DB
          value: chatbot_db
        - name: POSTGRES_USER
          value: chatbot_user
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

**api-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chatbot-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chatbot-api
  template:
    metadata:
      labels:
        app: chatbot-api
    spec:
      containers:
      - name: api
        image: your-registry/chatbot-api:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: gemini-api-key
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: secret-key
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: chatbot-api
spec:
  selector:
    app: chatbot-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

**secrets.yaml** (encrypt with sealed-secrets or use external secrets)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  database-url: postgresql://chatbot_user:PASSWORD@postgres:5432/chatbot_db
  gemini-api-key: YOUR_GEMINI_KEY
  secret-key: YOUR_SECRET_KEY
```

#### Step 2: Deploy to Kubernetes

```bash
# Create secrets
kubectl apply -f k8s/secrets.yaml

# Deploy database
kubectl apply -f k8s/postgres-deployment.yaml

# Deploy API
kubectl apply -f k8s/api-deployment.yaml

# Deploy workers
kubectl apply -f k8s/worker-deployment.yaml

# Check status
kubectl get pods
kubectl get services
```

### Option 3: Cloud Platforms

#### AWS Deployment

**Using ECS (Elastic Container Service)**

1. Push Docker image to ECR
2. Create ECS task definitions for API and workers
3. Use RDS PostgreSQL with pgvector extension
4. Use ElastiCache for Redis
5. Use ALB for load balancing
6. Use EFS for shared uploads directory

**Using EKS (Elastic Kubernetes Service)**

Follow Kubernetes deployment above on EKS cluster.

#### Google Cloud Platform

**Using Cloud Run**

1. Build and push to GCR
2. Deploy API as Cloud Run service
3. Use Cloud SQL for PostgreSQL
4. Use Memorystore for Redis
5. Use Cloud Tasks for background jobs

#### Azure Deployment

**Using Azure Container Instances**

1. Push to Azure Container Registry
2. Deploy using Container Instances
3. Use Azure Database for PostgreSQL
4. Use Azure Cache for Redis

## SSL/HTTPS Configuration

### Option 1: Nginx Reverse Proxy

Create `nginx.conf`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Add to `docker-compose.yml`:
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/conf.d/default.conf
    - ./ssl:/etc/nginx/ssl
  depends_on:
    - api
```

### Option 2: Let's Encrypt with Certbot

```bash
# Install certbot
docker-compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d yourdomain.com

# Auto-renewal
0 0 * * * docker-compose run --rm certbot renew
```

## Database Optimization

### Connection Pooling

In `database.py`:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,        # Increase for production
    max_overflow=40,     # Allow burst traffic
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600    # Recycle connections every hour
)
```

### Indexing

```sql
-- Create additional indexes for performance
CREATE INDEX CONCURRENTLY idx_chatlogs_created_at 
ON chat_logs(client_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_documents_created_at 
ON documents(client_id, created_at DESC);

-- Analyze tables
ANALYZE clients;
ANALYZE users;
ANALYZE documents;
ANALYZE chat_logs;
```

### Vacuum and Maintenance

```bash
# Schedule regular maintenance
docker-compose exec postgres psql -U chatbot_user -d chatbot_db -c "VACUUM ANALYZE;"

# Add to cron
0 2 * * * docker-compose exec postgres psql -U chatbot_user -d chatbot_db -c "VACUUM ANALYZE;"
```

## Monitoring Setup

### Prometheus + Grafana

Add to `docker-compose.yml`:
```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Application Logging

Add to `main.py`:
```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=10485760, backupCount=10),
        logging.StreamHandler()
    ]
)
```

## Backup Strategy

### Automated Database Backups

Create `backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="chatbot_backup_$DATE.sql"

docker-compose exec -T postgres pg_dump -U chatbot_user chatbot_db > "$BACKUP_DIR/$FILENAME"

# Compress
gzip "$BACKUP_DIR/$FILENAME"

# Upload to S3 (optional)
aws s3 cp "$BACKUP_DIR/$FILENAME.gz" s3://your-bucket/backups/

# Keep only last 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```

Schedule with cron:
```bash
0 2 * * * /path/to/backup.sh
```

## Performance Tuning

### API Server

```python
# In main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=4,              # Number of worker processes
        loop="uvloop",          # Faster event loop
        log_level="info",
        access_log=True
    )
```

### Celery Workers

```bash
# Increase concurrency
celery -A worker.celery_app worker \
  --loglevel=info \
  --concurrency=8 \
  --max-tasks-per-child=1000
```

### PostgreSQL

Edit `postgresql.conf`:
```conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

## Security Hardening

### 1. Environment Variables

Never commit `.env` to version control:
```bash
echo ".env" >> .gitignore
```

### 2. Database Security

```sql
-- Revoke public access
REVOKE ALL ON DATABASE chatbot_db FROM PUBLIC;

-- Grant specific permissions
GRANT CONNECT ON DATABASE chatbot_db TO chatbot_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO chatbot_user;
```

### 3. API Rate Limiting

Install slowapi:
```bash
pip install slowapi
```

Add to `main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, ...):
    ...
```

### 4. CORS Configuration

Update in `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
```

## Health Checks and Monitoring

### Uptime Monitoring

Use services like:
- UptimeRobot
- Pingdom
- StatusCake

Configure to check `https://yourdomain.com/health` every 5 minutes.

### Error Tracking

Integrate Sentry:
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
)
```

## Troubleshooting

### Common Issues

**1. Database connection errors**
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify connection
docker-compose exec postgres psql -U chatbot_user -d chatbot_db
```

**2. Celery tasks not processing**
```bash
# Check worker logs
docker-compose logs worker

# Inspect Redis queue
docker-compose exec redis redis-cli LLEN celery
```

**3. High memory usage**
```bash
# Monitor container resources
docker stats

# Restart services
docker-compose restart
```

## Rollback Procedure

```bash
# 1. Stop current version
docker-compose down

# 2. Restore database backup
docker-compose exec -T postgres psql -U chatbot_user chatbot_db < backup.sql

# 3. Checkout previous version
git checkout <previous-commit>

# 4. Rebuild and start
docker-compose up -d --build
```

## Cost Optimization

### Gemini API Costs

- Monitor token usage in chat_logs table
- Implement caching for common queries
- Set max_output_tokens limit
- Use cheaper models for simple queries

### Infrastructure Costs

- Use spot instances for workers
- Auto-scale based on load
- Use managed services (RDS, ElastiCache) for easier maintenance
- Implement CDN for static assets

## Compliance and Data Privacy

### GDPR Compliance

- Implement user data export endpoint
- Add data deletion endpoint
- Log all data access
- Encrypt sensitive data at rest

### Data Retention

```python
# Add to worker.py
@celery_app.task
def cleanup_old_data():
    """Delete data older than retention period"""
    from datetime import datetime, timedelta
    
    retention_days = 90
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    db = SessionLocal()
    try:
        # Delete old chat logs
        db.query(ChatLog).filter(ChatLog.created_at < cutoff_date).delete()
        db.commit()
    finally:
        db.close()
```

Schedule in Celery Beat:
```python
celery_app.conf.beat_schedule = {
    'cleanup-old-data': {
        'task': 'worker.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```
