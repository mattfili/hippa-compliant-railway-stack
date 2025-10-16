# HIPAA-Compliant Backend API

Production-ready FastAPI backend with OIDC/SAML authentication, multi-tenant context management, and HIPAA-compliant infrastructure patterns.

## Overview

This backend API scaffold provides a secure, compliant foundation for healthcare applications deployed on Railway with AWS infrastructure. It implements authentication, tenant isolation, structured logging, and health monitoring patterns required for HIPAA compliance.

### Key Features

- **JWT Authentication**: Token validation with JWKS endpoint integration and automatic key caching
- **Multi-Tenant Context**: Automatic tenant isolation extracted from JWT claims
- **HIPAA Compliance**: Structured logging, TLS encryption, and audit event documentation
- **Health Checks**: Kubernetes-style liveness and readiness endpoints
- **Database Connection**: Async SQLAlchemy with connection pooling and retry logic
- **Vector Search Ready**: PostgreSQL with pgvector extension enabled

## Architecture Summary

```
Client → [OIDC/SAML IdP] → Backend API
                           ├── Authentication Layer (JWT validation)
                           ├── Middleware (tenant context, logging, errors)
                           ├── API Routes (/api/v1/auth, /api/v1/health)
                           └── Database (PostgreSQL with pgvector)
```

**Integrations:**
- AWS Secrets Manager (runtime secret management)
- AWS KMS (encryption key management - future)
- RDS PostgreSQL (database with BAA coverage)
- CloudWatch (centralized logging via Railway)

## Prerequisites

Before starting, ensure you have:

- **Python 3.11+** installed
- **Docker** and Docker Compose (for local PostgreSQL)
- **Railway CLI** (for deployment): `npm install -g @railway/cli`
- **AWS Account** with Business Associate Agreement (BAA) signed
- **Identity Provider** (AWS Cognito, Okta, Auth0, or Azure AD) with OIDC/SAML support

## Quickstart (Local Development)

Get the application running locally in under 5 minutes:

### 1. Install Dependencies

```bash
# Install uv package manager (if not already installed)
pip install uv

# Install project dependencies
cd backend
uv sync
```

### 2. Start PostgreSQL

```bash
# Start PostgreSQL with Docker Compose
docker compose up -d postgres

# Or use Docker directly
docker run -d \
  --name hipaa-postgres \
  -e POSTGRES_USER=hipaa_user \
  -e POSTGRES_PASSWORD=hipaa_pass \
  -e POSTGRES_DB=hipaa_db \
  -p 5432:5432 \
  pgvector/pgvector:pg15
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your local settings
# At minimum, update DATABASE_URL to match your PostgreSQL instance
DATABASE_URL=postgresql+asyncpg://hipaa_user:hipaa_pass@localhost:5432/hipaa_db
```

### 4. Run Database Migrations

```bash
# Run migrations to set up database schema
alembic upgrade head
```

### 5. Start the Application

```bash
# Start FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Verify Installation

Open your browser to:
- **API Root**: http://localhost:8000 (should return `{"status": "ok"}`)
- **Health Check**: http://localhost:8000/api/v1/health/live (future)
- **API Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

## Local Development Setup (Detailed)

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection URL | `postgresql+asyncpg://user:pass@localhost:5432/dbname` |
| `ENVIRONMENT` | Yes | Application environment | `development`, `staging`, `production` |
| `LOG_LEVEL` | No | Logging verbosity | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ALLOWED_ORIGINS` | Yes | CORS allowed origins (comma-separated) | `http://localhost:3000,http://localhost:5173` |
| `OIDC_ISSUER_URL` | Yes* | OIDC provider issuer URL | `https://cognito-idp.us-east-1.amazonaws.com/...` |
| `OIDC_CLIENT_ID` | Yes* | OIDC application client ID | `your_client_id` |
| `JWT_TENANT_CLAIM_NAME` | No | JWT claim name for tenant ID | `tenant_id` (default) |

*Required for authentication features (Task Groups 4-6)

### Database Migrations

```bash
# Create a new migration
alembic revision -m "description_of_changes"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current migration status
alembic current

# View migration history
alembic history
```

### Running Tests

```bash
# Install development dependencies
uv sync --group dev

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_health.py

# Run tests matching pattern
pytest -k "test_health"
```

### Code Quality Tools

```bash
# Format code with black
black app/ tests/

# Lint code with ruff
ruff check app/ tests/

# Type check with mypy
mypy app/

# Run all quality checks
black app/ tests/ && ruff check app/ tests/ && mypy app/
```

## Railway Deployment

Deploy to Railway with one-click template deployment:

### 1. Fork Repository

Fork this repository to your GitHub account for continuous deployment.

### 2. Deploy Railway Template

1. Visit the Railway template link (or create new project)
2. Click "Deploy Now"
3. Connect your GitHub repository
4. Railway will automatically:
   - Provision a PostgreSQL database
   - Build the Docker container
   - Deploy the application

### 3. Configure Environment Variables

In Railway dashboard, set the following environment variables:

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://your-frontend-domain.com
OIDC_ISSUER_URL=https://your-idp.example.com
OIDC_CLIENT_ID=your_production_client_id
JWT_TENANT_CLAIM_NAME=tenant_id
AWS_REGION=us-east-1
AWS_SECRETS_MANAGER_SECRET_ID=hipaa-template/prod/secrets
```

**Note**: `DATABASE_URL` is automatically injected by Railway when you link the PostgreSQL service.

### 4. Configure AWS Secrets Manager

Store sensitive secrets in AWS Secrets Manager:

```bash
# Create secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name hipaa-template/prod/secrets \
  --secret-string '{"OIDC_CLIENT_SECRET":"your_secret_here"}' \
  --region us-east-1
```

Grant your Railway service IAM permissions:
1. Create IAM role for Railway service
2. Attach policy with `secretsmanager:GetSecretValue` permission
3. Configure Railway to assume this IAM role

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

### 5. Verify Deployment

Check health endpoints:
- **Liveness**: `https://your-app.railway.app/api/v1/health/live` (future)
- **Readiness**: `https://your-app.railway.app/api/v1/health/ready` (future)

View logs in Railway dashboard to confirm:
- Database migrations ran successfully
- Application started without errors
- Health checks returning 200 OK

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application factory
│   ├── config.py               # Settings and configuration (future)
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py         # Authentication endpoints (future)
│   │       └── health.py       # Health check endpoints (future)
│   ├── auth/
│   │   ├── jwt_validator.py    # JWT validation logic (future)
│   │   ├── tenant_extractor.py # Tenant ID extraction (future)
│   │   └── dependencies.py     # FastAPI auth dependencies (future)
│   ├── middleware/
│   │   ├── tenant_context.py   # Tenant isolation middleware (future)
│   │   ├── logging.py          # Request logging middleware (future)
│   │   └── exception.py        # Exception handling middleware (future)
│   ├── database/
│   │   ├── engine.py           # SQLAlchemy async engine
│   │   └── base.py             # Declarative base model
│   ├── models/                 # Database models (future features)
│   └── utils/
│       ├── logger.py           # JSON logging setup (future)
│       └── errors.py           # Error registry (future)
├── alembic/
│   ├── env.py                  # Alembic environment configuration
│   └── versions/               # Database migration files
├── tests/                      # Test files (future)
├── scripts/                    # Deployment scripts (future)
├── docs/                       # Additional documentation
├── Dockerfile                  # Multi-stage production build (future)
├── railway.json                # Railway deployment config (future)
├── pyproject.toml              # Project dependencies and tool config
└── .env.example                # Environment variable template
```

## Documentation

This README provides setup and deployment overview. For detailed information, see:

- **[API_ARCHITECTURE.md](docs/API_ARCHITECTURE.md)** - Extension points and architecture patterns
- **[AUTH_CONFIGURATION.md](docs/AUTH_CONFIGURATION.md)** - Identity provider setup guides
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Railway and AWS deployment details
- **[ERROR_CODES.md](docs/ERROR_CODES.md)** - Complete error code registry
- **[HIPAA_READINESS.md](docs/HIPAA_READINESS.md)** - HIPAA compliance checklist
- **[RAILWAY_ENV.md](docs/RAILWAY_ENV.md)** - Railway environment variable reference

## Security & Compliance

This application implements HIPAA-compliant patterns:

- **Encryption in Transit**: TLS 1.2+ enforced for all connections
- **Access Logging**: Structured logs with user context (request_id, user_id, tenant_id)
- **No PHI in Logs**: Only reference IDs logged, never patient information
- **Unique User Identification**: JWT-based authentication with IdP integration
- **Multi-Factor Authentication**: Enforced at IdP level (AWS Cognito, Okta, etc.)
- **Tenant Isolation**: Automatic tenant context extraction and validation

### Business Associate Agreements

Ensure you have BAAs signed with:
- **AWS** (RDS, S3, KMS, Secrets Manager, CloudWatch, Bedrock)
- **Railway** (application hosting and deployment)
- **Identity Provider** (AWS Cognito, Okta, Auth0, or Azure AD)

## Extending the Template

### Adding New API Domains

See [API_ARCHITECTURE.md](docs/API_ARCHITECTURE.md) for detailed examples.

```python
# Create new router in app/api/v1/documents.py
from fastapi import APIRouter, Depends, Request

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.get("/")
async def list_documents(request: Request):
    tenant_id = request.state.tenant_id  # Tenant context from middleware
    # Query documents for this tenant
    return {"documents": []}

# Register in app/main.py
from app.api.v1 import documents
app.include_router(documents.router, prefix="/api/v1")
```

### Adding Custom Middleware

```python
# Create middleware in app/middleware/custom.py
from fastapi import Request

async def custom_middleware(request: Request, call_next):
    # Pre-request processing
    response = await call_next(request)
    # Post-request processing
    return response

# Register in app/main.py
app.middleware("http")(custom_middleware)
```

### Adding Error Codes

```python
# Extend ErrorRegistry in app/utils/errors.py
class ErrorRegistry:
    DOC_001 = "Document not found"
    DOC_002 = "Invalid document format"
    # ... add more error codes
```

Document new codes in [ERROR_CODES.md](docs/ERROR_CODES.md).

## Troubleshooting

### Database Connection Fails

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Verify DATABASE_URL is correct
echo $DATABASE_URL

# Test connection manually
psql $DATABASE_URL -c "SELECT 1"
```

### Migrations Fail

```bash
# Check current migration status
alembic current

# View migration history
alembic history

# Reset to specific revision
alembic downgrade <revision_id>
alembic upgrade head
```

### Application Won't Start

```bash
# Check logs for errors
uvicorn app.main:app --log-level debug

# Verify all dependencies installed
uv sync

# Check environment variables loaded
python -c "import os; print(os.getenv('DATABASE_URL'))"
```

### Health Check Returns 503

```bash
# Check database connectivity (future feature)
curl http://localhost:8000/api/v1/health/ready

# View detailed error in logs
# Logs will show which dependency check failed
```

## Contributing

### Development Workflow

1. Create feature branch from `main`
2. Make changes following code standards
3. Run quality checks: `black . && ruff check . && mypy app/`
4. Run tests: `pytest`
5. Commit with clear message
6. Push and create pull request

### Code Standards

- **Formatting**: Use `black` with 100-character line length
- **Linting**: Use `ruff` with configured rule set
- **Type Checking**: Use `mypy` for static type analysis
- **Testing**: Write tests for critical workflows (authentication, health checks, tenant context)

## Support

For questions or issues:
1. Check documentation in `docs/` directory
2. Review [ERROR_CODES.md](docs/ERROR_CODES.md) for error explanations
3. Check Railway deployment logs
4. Review [HIPAA_READINESS.md](docs/HIPAA_READINESS.md) for compliance questions

## License

Proprietary

## Next Steps

This scaffold provides the foundation for healthcare applications. Future features to implement:

- **User & Tenant Management** (Feature 2) - Add user and tenant database models
- **AWS Infrastructure** (Feature 3) - Provision VPC, RDS, S3, KMS via Terraform
- **Document Ingestion** (Feature 5) - API endpoints for document upload and storage
- **Audit Logging** (Feature 10) - Immutable audit trail for HIPAA compliance
- **Authorization & RBAC** (Feature 13) - Role-based access control system

See project roadmap for complete feature list and timeline.
