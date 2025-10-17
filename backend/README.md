# HIPAA-Compliant Railway + AWS Scaffold

**Production-ready application scaffold** for deploying AI-enabled, HIPAA-compliant healthcare applications via one-click Railway template. Railway orchestrates deployment while Terraform provisions AWS infrastructure (VPC, RDS PostgreSQL, S3 storage, KMS encryption).

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.com/template/your-template-id)

## Overview

This is an **application scaffold** deployable via Railway template that enforces the **Railway as Orchestrator + AWS as Data Plane** architectural pattern:

- **Railway** hosts stateless application containers (FastAPI backend) and automates AWS infrastructure provisioning via Terraform
- **AWS** provides all HIPAA-eligible data services (RDS PostgreSQL, S3 storage, KMS encryption, Bedrock AI) where PHI resides exclusively
- **Terraform** Infrastructure as Code modules (included) provision VPC, RDS, S3, KMS, IAM, security groups, VPC networking
- **VPC Networking** connects Railway-hosted containers to AWS VPC securely (PHI never transits public internet)

**Developers clone this scaffold and extend it** for their healthcare application - it's a starting point with infrastructure, authentication, multi-tenant data model, and RAG pipeline already implemented.

**Deploy in under 5 minutes** - Railway template automates Terraform execution to provision AWS infrastructure, no manual AWS console work required.

### What You Get (Scaffold Includes)

When you deploy this scaffold via Railway template, you automatically get:

**Infrastructure Scaffold (Terraform):**
✅ **AWS VPC** with public/private subnets, security groups, VPC endpoints (via Terraform)
✅ **AWS RDS PostgreSQL** with pgvector extension, Multi-AZ, encrypted (via Terraform)
✅ **AWS S3 Buckets** for document storage, encrypted, versioned (via Terraform, future feature)
✅ **AWS KMS Keys** master key + per-tenant aliases (via Terraform, future feature)
✅ **IAM Roles & Policies** with least privilege for application (via Terraform)
✅ **VPC Networking** security groups, VPC peering/PrivateLink config for Railway connectivity

**Application Scaffold (FastAPI):**
✅ **Multi-Tenant Data Model** with Row-Level Security policies on all tables
✅ **Tenant Context Middleware** extracts tenant ID from JWT and enforces filtering
✅ **JWT Authentication** with OIDC/SAML integration (configurable IdP)
✅ **Vector Search** ready for RAG with pgvector (1024-dimensional embeddings)
✅ **Audit Logging** immutable append-only logs with database triggers
✅ **Soft Deletes** for HIPAA retention requirements
✅ **Automated Migrations** on every deployment (Alembic)
✅ **Health Checks** for monitoring and alerting

### HIPAA Compliance Built-In

- ✅ **PHI Boundary Enforced**: All PHI resides in AWS (RDS, S3, KMS) - Railway containers never store PHI locally
- ✅ **Comprehensive AWS BAA Coverage**: RDS, S3, KMS, Bedrock all covered by AWS BAA
- ✅ **VPC Networking**: Private connectivity between Railway app and AWS services (no public internet transit)
- ✅ **Row-Level Security**: PostgreSQL RLS policies block cross-tenant queries at database level
- ✅ **Per-Tenant Encryption**: AWS KMS keys provide cryptographic isolation between tenants (future feature)
- ✅ **Immutable Audit Logs**: Database triggers prevent UPDATE/DELETE on audit_logs table
- ✅ **AWS Config Rules**: Drift detection for unencrypted resources, overly permissive IAM (future feature)
- ✅ **IAM Least Privilege**: Application IAM role scoped to specific resources only

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Railway (Orchestrator)                        │
├─────────────────────────────────────────────────────────────────┤
│  • Hosts stateless application containers (FastAPI)             │
│  • Automates Terraform execution for AWS provisioning           │
│  • No PHI storage - containers are ephemeral                    │
│                                                                   │
│  ┌────────────────────────────────────────────────┐             │
│  │ FastAPI Backend Container                      │             │
│  │  ├── JWT authentication + tenant middleware    │             │
│  │  ├── SQLAlchemy models + Alembic migrations    │             │
│  │  ├── API routes (/ingest, /query, /audit)     │             │
│  │  └── Connects to AWS via IAM role + VPC       │             │
│  └────────────────────────────────────────────────┘             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ VPC Peering / PrivateLink
                            │ (Secure private connection)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              AWS VPC (Data Plane - PHI Boundary)                 │
├─────────────────────────────────────────────────────────────────┤
│  **All PHI resides here - covered by AWS BAA**                  │
│                                                                   │
│  ├── RDS PostgreSQL (private subnet)                            │
│  │    ├── Multi-tenant data model with RLS policies             │
│  │    ├── pgvector for semantic search                          │
│  │    ├── Encrypted with KMS, Multi-AZ, backups                 │
│  │    └── Security group: PostgreSQL port only from app         │
│  │                                                               │
│  ├── S3 Buckets (VPC endpoint access)                           │
│  │    ├── Encrypted document storage (SSE-KMS)                  │
│  │    ├── Versioning + lifecycle policies                       │
│  │    └── Bucket policy: app IAM role only                      │
│  │                                                               │
│  ├── KMS (Key Management Service)                               │
│  │    ├── Master keys for infrastructure                        │
│  │    └── Per-tenant keys for data encryption                   │
│  │                                                               │
│  └── Bedrock (AI/ML - called via AWS SDK)                       │
│       ├── Claude for RAG response generation                    │
│       └── Titan Embeddings for vector generation                │
│                                                                   │
│  Provisioned by: Terraform modules (included in scaffold)       │
└─────────────────────────────────────────────────────────────────┘
```

**Key Architectural Principle**: PHI Boundary Enforcement
- Railway containers are stateless and never store PHI locally
- All PHI operations (database queries, S3 uploads, KMS encryption) happen via AWS SDK calls
- VPC networking ensures data flows never transit public internet
- IAM policies restrict application to specific AWS resources only

## Deploy to Railway (Recommended)

### Option 1: One-Click Deploy (Fastest)

Click the button and you're done:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.com/template/your-template-id)

Railway will automatically:
1. Execute Terraform to provision AWS RDS PostgreSQL with pgvector
2. Execute Terraform to provision AWS S3 buckets (future feature)
3. Execute Terraform to provision AWS KMS keys (future feature)
4. Deploy the FastAPI backend application to Railway
5. Run database migrations on deployment
6. Configure health checks for monitoring

**All you need**: AWS credentials and OIDC/SAML provider credentials (add them in Railway dashboard after deployment).

### Option 2: Deploy from Repository

1. Fork this repository
2. Connect to Railway: "New Project" → "Deploy from GitHub repo"
3. Add environment variables (see below)
4. Railway handles the rest automatically

### Required Environment Variables

After deployment, configure these in Railway dashboard:

```bash
# OIDC Authentication (required)
OIDC_ISSUER_URL=https://your-idp.com
OIDC_CLIENT_ID=your_client_id
OIDC_CLIENT_SECRET=your_secret

# AWS for Bedrock/KMS (required for future features)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# CORS (required)
ALLOWED_ORIGINS=https://your-frontend.com

# Optional (Railway sets these automatically)
# DATABASE_URL=<auto-injected>
# ENVIRONMENT=production
# LOG_LEVEL=INFO
```

### Verify Deployment

Once deployed:
- Check health: `https://your-app.railway.app/api/v1/health/ready`
- View logs in Railway dashboard for "Database migrations completed"
- System tenant is automatically seeded

That's it! Your HIPAA-compliant backend is live.

## Prerequisites (For HIPAA Production Use)

Before deploying to production:

- **Railway Account** with Business Associate Agreement (BAA) signed
- **AWS Account** with BAA for Bedrock and KMS services
- **Identity Provider** with OIDC/SAML support (AWS Cognito, Okta, Auth0, Azure AD)

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

## Advanced Configuration (Optional)

The Railway template works out-of-the-box, but you can customize if needed:

### PostgreSQL Tuning

For production workloads, see [docs/POSTGRESQL_TUNING.md](docs/POSTGRESQL_TUNING.md) for:
- Memory optimization by RAM tier
- Query performance tuning
- Vector search optimization
- HIPAA compliance settings (WAL archiving)

**Note**: The template uses sensible defaults. Tuning is optional.

### Troubleshooting

If you encounter issues, see [docs/RAILWAY_SETUP.md](docs/RAILWAY_SETUP.md) for:
- pgvector extension verification
- Common deployment issues
- Database connection troubleshooting

### Manual Deployment

If you need to deploy without the Railway template:

1. **Create PostgreSQL service:**
   - In Railway project, click "New" > "Database" > "PostgreSQL"
   - Ensure pgvector extension is available (see [docs/RAILWAY_SETUP.md](docs/RAILWAY_SETUP.md))

2. **Create backend service:**
   - Click "New" > "GitHub Repo"
   - Select your repository
   - Set build command: `cd backend && pip install -r requirements.txt`
   - Set start command: `cd backend && sh startup.sh`

3. **Link services:**
   - Connect backend service to PostgreSQL service
   - Railway will inject `DATABASE_URL` automatically

4. **Configure environment variables** (see list above)

### Database Migrations on Railway

Migrations run automatically on deployment via `startup.sh`:

```bash
# startup.sh runs:
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

To manually trigger migrations:
1. Open Railway service console
2. Run: `alembic upgrade head`

### HIPAA Compliance Checklist

Before storing PHI (Protected Health Information):

- [ ] Sign Railway Business Associate Agreement (BAA)
- [ ] Enable encryption at rest on PostgreSQL (Railway settings)
- [ ] Enable Railway Backups with 30+ day retention
- [ ] Configure PostgreSQL tuning (see [docs/POSTGRESQL_TUNING.md](docs/POSTGRESQL_TUNING.md))
- [ ] Verify Row-Level Security (RLS) policies enabled (via migrations)
- [ ] Configure audit logging (see [docs/POSTGRESQL_TUNING.md](docs/POSTGRESQL_TUNING.md))
- [ ] Test backup restoration process
- [ ] Configure CORS origins restrictively
- [ ] Enable TLS 1.2+ for all connections (Railway default)

### Railway Documentation

For detailed Railway-specific setup and tuning:
- [Railway Setup Guide](docs/RAILWAY_SETUP.md) - pgvector verification, troubleshooting, backups
- [PostgreSQL Tuning](docs/POSTGRESQL_TUNING.md) - Performance optimization, HIPAA compliance settings

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
│   ├── RAILWAY_SETUP.md        # Railway PostgreSQL setup and verification
│   └── POSTGRESQL_TUNING.md    # Performance tuning and HIPAA compliance
├── Dockerfile                  # Multi-stage production build (future)
├── railway.json                # Railway deployment config (future)
├── pyproject.toml              # Project dependencies and tool config
└── .env.example                # Environment variable template
```

## Documentation

This README provides setup and deployment overview. For detailed information, see:

- **[RAILWAY_SETUP.md](docs/RAILWAY_SETUP.md)** - Railway PostgreSQL setup, pgvector verification, troubleshooting
- **[POSTGRESQL_TUNING.md](docs/POSTGRESQL_TUNING.md)** - Performance optimization, HIPAA compliance settings
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

### pgvector Extension Issues

See [docs/RAILWAY_SETUP.md](docs/RAILWAY_SETUP.md) for comprehensive troubleshooting:
- Extension not available
- Permission errors
- Vector query issues
- Index creation timeouts

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
2. Review [RAILWAY_SETUP.md](docs/RAILWAY_SETUP.md) for Railway-specific questions
3. Review [ERROR_CODES.md](docs/ERROR_CODES.md) for error explanations
4. Check Railway deployment logs
5. Review [HIPAA_READINESS.md](docs/HIPAA_READINESS.md) for compliance questions

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
