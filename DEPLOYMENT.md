# NDA Reviewer - Deployment Guide

## Local Development Setup

### 1. Initial Setup

```bash
# Navigate to project
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\20251005_211648"

# Install dependencies
cd backend
pip install -r requirements.txt

# Create environment file
cp .env.template .env
```

### 2. Configure API Keys

Edit `backend/.env`:

```env
# Required for LLM analysis
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional configuration
USE_PROMPT_CACHING=true
VALIDATION_RATE=0.15
CONFIDENCE_THRESHOLD=95
```

### 3. Start Server

**Option A: Using start script**
```bash
python start_server.py
```

**Option B: Direct uvicorn**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Option C: Python module**
```bash
cd backend
python -m app.main
```

### 4. Verify Installation

```bash
# Health check
curl http://localhost:8000/

# API documentation
open http://localhost:8000/docs
```

## Testing

### Run Training Corpus Tests

```bash
python test_training_corpus.py
```

Expected output:
```
TRAINING CORPUS TEST
==================================================
Testing: Project Central - NDA.docx
  Expected changes: 126
  Generated redlines: 118
  Estimated accuracy: 93.7%

TEST SUMMARY
==================================================
Average accuracy: 94.2%
Average redlines per document: 95.6
```

### Test Single Document

```bash
# Upload
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@test_nda.docx" \
  | jq -r '.job_id'

# Check status (replace JOB_ID)
curl "http://localhost:8000/api/jobs/JOB_ID/status" | jq

# Download redlined
curl "http://localhost:8000/api/jobs/JOB_ID/download" \
  -o redlined.docx
```

## Production Deployment

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/app ./app
COPY backend/.env .env

# Create storage directories
RUN mkdir -p storage/uploads storage/working storage/exports

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t nda-reviewer .
docker run -p 8000:8000 -v ./storage:/app/storage nda-reviewer
```

### Docker Compose (with Redis)

`docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./storage:/app/storage
      - ./backend/.env:/app/.env
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  worker:
    build: .
    command: python -m app.workers.document_worker
    volumes:
      - ./storage:/app/storage
      - ./backend/.env:/app/.env
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

volumes:
  redis_data:
```

Run:
```bash
docker-compose up -d
```

### Cloud Deployment (AWS)

#### Option 1: ECS Fargate

1. **Build and push Docker image**:
```bash
aws ecr create-repository --repository-name nda-reviewer

docker build -t nda-reviewer .
docker tag nda-reviewer:latest {ECR_URL}/nda-reviewer:latest
docker push {ECR_URL}/nda-reviewer:latest
```

2. **Create task definition**:
```json
{
  "family": "nda-reviewer",
  "taskRoleArn": "arn:aws:iam::...",
  "executionRoleArn": "arn:aws:iam::...",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "nda-reviewer-api",
      "image": "{ECR_URL}/nda-reviewer:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "OPENAI_API_KEY", "value": "..."},
        {"name": "ANTHROPIC_API_KEY", "value": "..."}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/nda-reviewer",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048"
}
```

3. **Create service**:
```bash
aws ecs create-service \
  --cluster nda-cluster \
  --service-name nda-reviewer \
  --task-definition nda-reviewer \
  --desired-count 2 \
  --launch-type FARGATE \
  --load-balancers targetGroupArn=...,containerName=nda-reviewer-api,containerPort=8000
```

#### Option 2: Lambda + API Gateway

For serverless deployment, modify to use AWS Lambda handler.

### Environment Variables

Production `.env`:

```env
# API Keys (use AWS Secrets Manager in production)
OPENAI_API_KEY=${OPENAI_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# LLM Configuration
USE_PROMPT_CACHING=true
VALIDATION_RATE=0.15
CONFIDENCE_THRESHOLD=95

# Processing
MAX_PROCESSING_TIME=60
WORKER_CONCURRENCY=4

# Storage (use S3 in production)
STORAGE_PATH=/app/storage
RETENTION_DAYS=7

# Security
API_KEY=${API_KEY}
CORS_ORIGINS=https://your-domain.com

# Redis (if using)
REDIS_URL=redis://redis:6379

# Monitoring
SENTRY_DSN=${SENTRY_DSN}
LOG_LEVEL=INFO
```

## Monitoring & Logging

### Add Sentry Integration

```bash
pip install sentry-sdk[fastapi]
```

In `app/main.py`:

```python
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=1.0,
)
```

### CloudWatch Logs

Configure in ECS task definition or add boto3 logging handler.

### Metrics to Monitor

- **Processing Time**: Average time per document
- **Error Rate**: Failed jobs / total jobs
- **LLM Costs**: Track API usage
- **Accuracy**: Compare to training baseline
- **Queue Length**: Pending jobs

## Scaling Considerations

### Horizontal Scaling

1. **Use Redis for job queue**: Replace in-memory queue
2. **Run multiple workers**: Set `WORKER_CONCURRENCY`
3. **Load balancer**: Distribute API requests

### Vertical Scaling

- Minimum: 2GB RAM, 1 CPU
- Recommended: 4GB RAM, 2 CPUs
- Heavy load: 8GB RAM, 4 CPUs

### Cost Optimization

1. **Enable prompt caching**: Saves 60-70% on LLM costs
2. **Batch processing**: Group similar documents
3. **Rule-only mode**: Skip LLM for simple documents
4. **Spot instances**: AWS Fargate Spot for workers

## Security Checklist

- [ ] API keys in secrets manager (not .env)
- [ ] CORS configured for production domain
- [ ] File upload size limits enforced
- [ ] Input validation on all endpoints
- [ ] Rate limiting implemented
- [ ] HTTPS only in production
- [ ] Logs don't contain PII
- [ ] Files auto-deleted after retention period
- [ ] API authentication enabled
- [ ] Network security groups configured

## Backup & Recovery

### Database Backup

If using PostgreSQL for job metadata:
```bash
pg_dump nda_reviewer > backup.sql
```

### File Storage Backup

If using S3:
```bash
aws s3 sync s3://nda-storage s3://nda-backup --storage-class GLACIER
```

### Disaster Recovery

1. **RTO (Recovery Time Objective)**: < 1 hour
2. **RPO (Recovery Point Objective)**: < 5 minutes

Backup strategy:
- Continuous: Job metadata to RDS with Multi-AZ
- Daily: S3 storage to Glacier
- Weekly: Full system snapshot

## Troubleshooting Production Issues

### High Memory Usage

```bash
# Check container memory
docker stats

# Increase memory limit
# Update task definition memory to 4096 or 8192
```

### Slow Processing

```bash
# Check Redis queue length
redis-cli LLEN job_queue

# Scale workers
docker-compose up -d --scale worker=4
```

### API Errors

```bash
# Check logs
docker-compose logs -f api

# Check health endpoint
curl http://api/health
```

### LLM Timeouts

- Increase `MAX_PROCESSING_TIME` in .env
- Check API rate limits
- Verify API keys are valid

## Maintenance

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt
```

### Cleanup Old Files

```bash
# Manual cleanup
find storage/uploads -mtime +7 -delete
find storage/exports -mtime +7 -delete

# Or set up cron job
0 0 * * * find /app/storage -mtime +7 -delete
```

### Update Rules

Edit `backend/app/models/rules.yaml` and restart service:

```bash
docker-compose restart api
```

## Performance Benchmarks

Target performance (single instance):

- **Throughput**: 60-80 documents/hour
- **Latency**: 45-60 seconds per document
- **Concurrent Jobs**: 4-8
- **Memory**: 1.5-2GB per worker
- **CPU**: 60-80% utilization

## Support & Maintenance

### Regular Tasks

- **Weekly**: Review error logs, check accuracy metrics
- **Monthly**: Update dependencies, review rules effectiveness
- **Quarterly**: Re-test against training corpus, optimize prompts

### Alerts to Configure

1. Error rate > 5%
2. Processing time > 90 seconds
3. Memory usage > 90%
4. Queue length > 100
5. LLM API errors

---

**Last Updated**: 2025-10-05
**Version**: 1.0.0
