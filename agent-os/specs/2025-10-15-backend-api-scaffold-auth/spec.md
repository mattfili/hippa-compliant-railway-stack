# Specification: Backend API Scaffold with Authentication

## Goal

Establish a production-ready FastAPI backend foundation with OIDC/SAML authentication, tenant context management, and HIPAA-compliant infrastructure patterns that serves as the base for all subsequent features in the Railway template.

## User Stories

- As a healthcare application developer, I want to deploy a HIPAA-compliant API in under 1 hour so that I can focus on building product features instead of compliance infrastructure
- As a healthcare startup engineer, I want authentication to work with any enterprise IdP (Okta, Auth0, Azure AD, AWS Cognito) so that my customers can use their existing identity systems with MFA
- As a SaaS platform developer, I want automatic tenant isolation built into every request so that I never accidentally leak data across healthcare organizations
- As a template user, I want clear documentation on where to add new features so that I can extend the scaffold without breaking compliance patterns
- As a compliance officer, I want all authentication events structured and logged so that audit trails are ready for HIPAA reviews

## Core Requirements

### Functional Requirements

**Authentication & Authorization**
- JWT token validation using IdP's JWKS endpoint with automatic key caching and refresh
- Support for OIDC/SAML authentication flows (IdP-agnostic design)
- Token expiration enforcement with maximum 60-minute lifetime
- Authentication endpoints: login callback, token validation, logout
- Configuration examples for AWS Cognito with documentation for other IdPs

**Tenant Context Management**
- Middleware extracting tenant_id from JWT custom claims (tenant_id or organization_id fields)
- Tenant context injection into request state for downstream access
- No fallback tenant resolution methods (fail explicitly if tenant_id missing)
- Request-scoped tenant validation on all authenticated endpoints

**API Structure**
- Domain-based route organization with versioning: /api/v1/{domain}/*
- Implemented routes: /api/v1/auth/* (login, logout, validate) and /api/v1/health/* (liveness, readiness)
- Documented but unimplemented: /api/v1/documents/* structure showing future integration points
- Router registration pattern supporting modular addition of new domains

**Health & Status Endpoints**
- Liveness check: Returns 200 OK if application is running (< 100ms response time)
- Readiness check: Validates database connectivity and returns detailed status

**Error Handling**
- Standardized error response format: `{"error": {"code": "AUTH_001", "message": "Invalid token", "detail": "Token expired"}}`
- Comprehensive error code registry in separate documentation (AUTH_001-999 for auth, SYS_001-999 for system)
- Human-readable messages with technical details for debugging
- No PHI in error messages or logs (use IDs only)

**Logging System**
- Structured JSON logging with fields: timestamp, level, request_id, tenant_id, user_id, message, context
- Log levels: DEBUG, INFO, WARNING, ERROR
- Output to stdout for Railway automatic CloudWatch integration
- Document HIPAA audit events for future implementation: auth attempts, auth failures, permission denials

**CORS Configuration**
- Configurable allowed origins via ALLOWED_ORIGINS environment variable
- Support for credentials (cookies) for refresh token flows
- Permissive localhost defaults for development (localhost:3000, localhost:5173)
- Require explicit production origin specification (no wildcards)

**Database Connection**
- SQLAlchemy 2.0 async engine with connection pooling (pool_size=10-20)
- Automatic reconnection logic for transient database failures
- Connection timeouts configured (pool_timeout=30s, connect_timeout=10s)
- Alembic migration framework with initial migration for base schema

### Non-Functional Requirements

**Performance**
- Health check response time: < 100ms
- Authentication request processing: < 500ms (excluding external IdP validation)
- JWKS key cache TTL: 1 hour with background refresh

**Security**
- TLS 1.2+ enforced for all connections (database, S3, external APIs)
- JWT signature verification on every request
- Tenant isolation via middleware (no shared tenant access)
- Secrets stored in AWS Secrets Manager, not environment variables
- CORS restricted to explicit origins in production environments

**Reliability**
- Graceful degradation when IdP JWKS endpoint temporarily unavailable (use cached keys)
- Database connection retry with exponential backoff (max 3 retries)
- Structured error responses even for unexpected exceptions

**HIPAA Compliance**
- Unique user identification via IdP (no anonymous access to PHI endpoints)
- Access logging with user context (request_id, user_id, tenant_id)
- No PHI in application logs (only reference IDs)
- Encryption in transit for all network communication

**Developer Experience**
- Clear project structure with separation of concerns
- Environment variable templates for local (.env.example) and Railway deployment
- Pre-commit hooks for code quality (black, ruff, mypy)
- Automatic OpenAPI documentation via FastAPI

## Visual Design

No visual assets provided. This is a backend API scaffold with no user-facing UI.

Architecture diagram provided in requirements shows:
- Client authentication via OIDC/SAML → Backend API Layer
- Backend components: Authentication/Authorization, Multi-tenant context, Audit logging (documented only)
- Integration points: AWS KMS (key management), RDS PostgreSQL (database), CloudWatch (logs)
- Future extension points: Document ingestion APIs, Query/RAG APIs (documented architecture only)

## Reusable Components

### Existing Code to Leverage

This is a greenfield project - no existing code to reuse. However, the following open-source libraries will be leveraged:

**Core Framework**
- FastAPI: Web framework with automatic OpenAPI docs
- Pydantic: Data validation (built into FastAPI)
- SQLAlchemy 2.0: Async ORM with connection pooling

**Authentication**
- python-jose: JWT token parsing and validation
- httpx: Async HTTP client for JWKS endpoint calls

**Logging**
- Python standard logging with custom JSON formatter (or structlog)

**Database Migrations**
- Alembic: Database migration tool for SQLAlchemy

**Code Quality**
- black: Code formatting
- ruff: Fast Python linter
- mypy: Static type checking

### New Components Required

**Custom Middleware**
- Tenant context middleware: Extract tenant_id from JWT, inject into request state, validate access
- Logging middleware: Add request_id, tenant_id, user_id to all log records
- Exception handling middleware: Convert exceptions to standardized error format

**Authentication Services**
- JWTValidator: Fetch JWKS keys, validate JWT signature and expiration, cache keys with TTL
- TenantExtractor: Parse JWT claims to extract tenant_id with configurable claim names
- AuthService: Coordinate authentication flow and token validation

**Configuration Management**
- Settings: Pydantic settings model loading from environment variables and AWS Secrets Manager
- SecretManager: Async client for fetching runtime secrets from AWS Secrets Manager

**Database Setup**
- AsyncDatabase: SQLAlchemy async engine factory with connection pooling
- BaseModel: SQLAlchemy declarative base with common fields (id, created_at, updated_at)

**Utilities**
- Logger: JSON logging configuration with context injection
- ErrorRegistry: Central registry of error codes and messages
- HealthCheck: Database connectivity validation for readiness endpoint

**Why These Components Are New**
- Tenant context extraction is domain-specific (healthcare multi-tenancy requirements)
- HIPAA-compliant logging patterns not available in standard libraries
- Error code registry pattern specific to compliance documentation needs
- AWS Secrets Manager integration customized for Railway deployment pattern

## Technical Approach

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application factory
│   ├── config.py               # Settings with env vars + AWS Secrets Manager
│   ├── middleware/
│   │   ├── tenant_context.py  # Tenant extraction middleware
│   │   ├── logging.py          # Request logging middleware
│   │   └── exception.py        # Exception handling middleware
│   ├── auth/
│   │   ├── jwt_validator.py   # JWT validation with JWKS
│   │   ├── tenant_extractor.py # Parse tenant from JWT claims
│   │   └── dependencies.py     # FastAPI dependencies for auth
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py         # Authentication endpoints
│   │       └── health.py       # Health check endpoints
│   ├── database/
│   │   ├── engine.py           # SQLAlchemy async engine setup
│   │   └── base.py             # Declarative base model
│   ├── models/                 # Empty for now (Feature 2)
│   ├── utils/
│   │   ├── logger.py           # JSON logging setup
│   │   └── errors.py           # Error registry and exceptions
├── alembic/
│   ├── env.py                  # Alembic configuration
│   └── versions/               # Migration files
├── tests/                      # Empty for now (Feature 17)
├── Dockerfile                  # Multi-stage production build
├── railway.json                # Railway deployment config
├── alembic.ini                 # Alembic configuration
├── pyproject.toml              # Project dependencies (uv)
└── .env.example                # Environment variable template
```

### Database Schema

Initial Alembic migration creates empty database with pgvector extension enabled. Core tables will be added in Feature 2.

Migration includes:
- Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
- Placeholder comment for future tenant, user, document tables

### API Endpoint Specification

**Authentication Endpoints**

`POST /api/v1/auth/callback`
- Purpose: Handle IdP callback after successful authentication
- Request: `{"code": "auth_code", "state": "csrf_token"}`
- Response: `{"access_token": "jwt_token", "token_type": "Bearer", "expires_in": 3600}`
- Errors: AUTH_001 (Invalid code), AUTH_002 (CSRF validation failed)

`GET /api/v1/auth/validate`
- Purpose: Validate current user's JWT token
- Headers: `Authorization: Bearer <token>`
- Response: `{"valid": true, "user_id": "123", "tenant_id": "org-456", "expires_at": 1234567890}`
- Errors: AUTH_003 (Token expired), AUTH_004 (Invalid signature), AUTH_005 (Missing tenant claim)

`POST /api/v1/auth/logout`
- Purpose: Invalidate session (IdP-side logout via redirect)
- Request: `{"redirect_uri": "https://app.example.com"}`
- Response: `{"logout_url": "https://idp.example.com/logout?..."}`
- Errors: AUTH_006 (Invalid redirect URI)

**Health Endpoints**

`GET /api/v1/health/live`
- Purpose: Kubernetes-style liveness probe
- Response: `{"status": "ok", "timestamp": 1234567890}`
- Always returns 200 unless application crashed

`GET /api/v1/health/ready`
- Purpose: Kubernetes-style readiness probe with dependency checks
- Response: `{"status": "ready", "checks": {"database": "ok", "secrets": "ok"}, "timestamp": 1234567890}`
- Returns 503 if dependencies unavailable
- Errors: SYS_001 (Database unreachable), SYS_002 (Secrets Manager unavailable)

### Authentication Flow Sequence

1. User accesses protected resource → redirected to IdP login
2. IdP authenticates user (MFA at IdP level) → redirects to callback URL with auth code
3. Backend receives callback → exchanges code for JWT token at IdP token endpoint
4. Backend validates JWT: fetch JWKS keys, verify signature, check expiration
5. Backend extracts tenant_id from custom JWT claim (fail if missing)
6. Backend creates session (or returns JWT to client for stateless auth)
7. Subsequent requests include JWT in Authorization header
8. Tenant context middleware extracts tenant_id, injects into request state
9. Route handlers access tenant context for tenant-scoped queries

### JWT Validation Implementation

**JWKS Caching Strategy**
- On first validation request: fetch JWKS from IdP endpoint (e.g., https://cognito.amazonaws.com/.well-known/jwks.json)
- Cache keys in memory with TTL (1 hour default, configurable)
- Background refresh before TTL expiration to prevent cache miss latency
- Retry logic for transient JWKS fetch failures (3 retries with exponential backoff)

**Token Validation Steps**
1. Parse JWT header to extract key ID (kid)
2. Lookup key in cache (fetch from JWKS if cache miss)
3. Verify signature using public key
4. Validate standard claims: exp (expiration), iat (issued at), iss (issuer)
5. Validate token expiration < 60 minutes from issued time
6. Extract custom claims: tenant_id or organization_id
7. Return decoded claims to caller

### Tenant Context Middleware

**Middleware Execution Flow**
1. Middleware executes after authentication dependency (JWT validation)
2. Extract decoded JWT claims from request state
3. Check for tenant_id or organization_id claim (configurable priority order)
4. If missing: return 403 Forbidden with error code AUTH_005 (Missing tenant claim)
5. Inject tenant context into request state: `request.state.tenant_id = "org-456"`
6. Continue to route handler

**Tenant Context Access Pattern**
```python
# In route handlers
async def get_documents(request: Request):
    tenant_id = request.state.tenant_id  # Always present after middleware
    # Use tenant_id for tenant-scoped queries
```

### Environment Variable Management

**Local Development (.env.example)**
```
# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname

# Authentication
OIDC_ISSUER_URL=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123
OIDC_CLIENT_ID=your_client_id
OIDC_CLIENT_SECRET=your_client_secret (reference to Secrets Manager)
JWT_TENANT_CLAIM_NAME=tenant_id

# AWS
AWS_REGION=us-east-1
AWS_SECRETS_MANAGER_SECRET_ID=hipaa-template/prod/secrets
```

**Railway Environment Variables (via railway.json)**
- Non-sensitive deployment config: DATABASE_URL, ENVIRONMENT, ALLOWED_ORIGINS
- Secrets in AWS Secrets Manager: OIDC_CLIENT_SECRET, encryption keys
- Railway automatically injects DATABASE_URL from linked Postgres service

**AWS Secrets Manager Integration**
- On startup: fetch runtime secrets from Secrets Manager using IAM role
- Cache secrets in memory (no disk writes)
- Retry logic for transient failures (prevent startup crashes)
- Future: automatic secret rotation handling (reload on SIGHUP)

### Logging Implementation

**Structured JSON Format**
```json
{
  "timestamp": "2025-10-15T12:34:56.789Z",
  "level": "INFO",
  "logger": "app.api.v1.auth",
  "message": "User authenticated successfully",
  "request_id": "req-123-abc-456",
  "user_id": "usr-789",
  "tenant_id": "org-456",
  "context": {
    "endpoint": "/api/v1/auth/validate",
    "method": "GET",
    "status_code": 200,
    "duration_ms": 45
  }
}
```

**Logging Middleware Implementation**
- Generate unique request_id (UUID4) at request start
- Inject request_id, tenant_id, user_id into logging context
- Log request start (DEBUG level): method, path, query params (sanitized)
- Log request completion (INFO level): status code, duration, error if failed
- Redact sensitive data from logs: Authorization headers, password fields

**HIPAA Audit Event Documentation** (for future Feature 10)
Document these event types for implementation in audit logging feature:
- AUTH_LOGIN_SUCCESS: User successfully authenticated
- AUTH_LOGIN_FAILED: Authentication attempt failed (capture: user_id_attempted, reason)
- AUTH_LOGOUT: User logged out
- AUTH_TOKEN_EXPIRED: Access denied due to expired token
- AUTH_PERMISSION_DENIED: Access denied due to insufficient permissions
- DATA_ACCESS: User accessed PHI data (capture: resource_type, resource_id)
- DATA_MODIFIED: User modified PHI data (capture: resource_type, resource_id, operation)

### Error Response Format Standard

**Standardized Error Structure**
```json
{
  "error": {
    "code": "AUTH_001",
    "message": "Invalid authentication token",
    "detail": "Token signature verification failed",
    "request_id": "req-123-abc-456"
  }
}
```

**Error Code Registry** (to be documented in docs/ERROR_CODES.md)
- AUTH_001: Invalid token (signature verification failed)
- AUTH_002: CSRF validation failed
- AUTH_003: Token expired
- AUTH_004: Invalid token signature
- AUTH_005: Missing tenant claim in JWT
- AUTH_006: Invalid redirect URI
- SYS_001: Database unreachable
- SYS_002: Secrets Manager unavailable
- SYS_003: Internal server error (unexpected exception)

**Exception Handling Middleware**
- Catch all unhandled exceptions
- Convert to standardized error format
- Log exception with full stack trace (ERROR level)
- Return appropriate HTTP status code
- Never expose stack traces to clients (only in logs)

### CORS Configuration

**Development Settings**
```python
allowed_origins = [
    "http://localhost:3000",  # Retool local
    "http://localhost:5173",  # Vite dev server
    "http://localhost:8080",  # Alternative frontend port
]
allow_credentials = True
```

**Production Settings**
```python
# Loaded from ALLOWED_ORIGINS environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS").split(",")
allow_credentials = True
```

**CORS Headers**
- Access-Control-Allow-Origin: Explicit origin (no wildcards with credentials)
- Access-Control-Allow-Credentials: true
- Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
- Access-Control-Allow-Headers: Authorization, Content-Type
- Access-Control-Max-Age: 86400 (24 hours)

## Deployment & Infrastructure

### Railway Deployment Configuration (railway.json)

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "sh scripts/startup.sh",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3,
    "healthcheckPath": "/api/v1/health/ready",
    "healthcheckTimeout": 30
  },
  "services": [
    {
      "name": "backend-api",
      "source": {
        "repo": "github.com/user/repo",
        "branch": "main"
      }
    }
  ]
}
```

### Dockerfile Specification

**Multi-Stage Build**
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
WORKDIR /app
RUN pip install uv
COPY pyproject.toml .
RUN uv sync --frozen

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY scripts/ scripts/
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["sh", "scripts/startup.sh"]
```

**Startup Script (scripts/startup.sh)**
```bash
#!/bin/sh
set -e
echo "Running database migrations..."
alembic upgrade head
echo "Starting application..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Alembic Migration Setup

**Initial Migration (versions/001_init_pgvector.py)**
- Enable pgvector extension
- Add comment documenting future table structure
- No tables created in this feature (deferred to Feature 2)

**Auto-Run Migrations for Base Deployment**
- Railway startup script runs `alembic upgrade head` before starting app
- First deployment creates pgvector extension automatically
- Future deployments run pending migrations automatically

**Manual Migrations for Template Users**
- Document in DEPLOYMENT.md that template users should run migrations manually
- Provide CLI command: `railway run alembic upgrade head`
- Safety: migrations should be idempotent and reversible

### Environment Variable Templates

**.env.example (Local Development)**
Complete example with inline comments explaining each variable, safe to commit to repository.

**Railway Environment Variable Template (docs/RAILWAY_ENV.md)**
List of required Railway environment variables with:
- Variable name
- Description
- Example value (non-sensitive)
- Whether it's auto-injected by Railway or user-provided
- Link to AWS Secrets Manager for sensitive values

## Security & Compliance

### HIPAA-Compliant Logging Practices

**What to Log**
- Authentication events (login, logout, token validation)
- Request metadata (method, path, status code, duration)
- User context (user_id, tenant_id, request_id)
- Error conditions (with sanitized error messages)

**What NOT to Log**
- Authorization headers or tokens
- Query parameters containing PHI (patient_id in URL)
- Request/response bodies containing PHI
- Database passwords or API keys
- Full exception stack traces to external logging (internal only)

**Log Sanitization**
- Redact authorization headers: "Authorization: Bearer ***"
- Redact sensitive query parameters: "?patient_id=***"
- Use reference IDs instead of patient names/SSNs

### Encryption Requirements

**TLS 1.2+ Configuration**
- Database connections: `?ssl=require&sslmode=verify-full` in connection string
- AWS API calls: httpx client enforces TLS 1.2+ (default in Python 3.11)
- Application endpoints: Railway/AWS ALB handles TLS termination

**At-Rest Encryption** (documented for future features)
- RDS encryption enabled with KMS (Feature 3)
- S3 server-side encryption with KMS (Feature 5)
- Application-level encryption for sensitive fields (Feature 4)

### Tenant Isolation Strategy

**Architectural Principles**
- Every authenticated request has exactly one tenant_id (no multi-tenant access)
- Tenant context extracted from JWT (not query params or headers)
- Middleware enforces tenant context before route handlers execute
- Database queries filter by tenant_id automatically (pattern for Feature 2)

**Tenant Validation**
- JWT must contain tenant_id claim (fail request if missing)
- Tenant ID format validation (e.g., "org-{uuid}")
- No cross-tenant queries allowed (enforced at middleware layer)

**Future Tenant Isolation** (documented for Feature 2)
- Database row-level security with tenant_id column
- Per-tenant encryption keys (Feature 4)
- Audit logs capture tenant_id for all operations

### Error Response Format (No PHI Leakage)

**Safe Error Messages**
- Use generic messages for client responses: "Authentication failed"
- Technical details only in logs: "JWKS key fetch failed: connection timeout"
- Error codes provide debugging hints without exposing internals
- Request ID allows correlation between client error and server logs

**Unsafe Patterns to Avoid**
- Including user emails/names in error messages
- Database constraint violation details (might leak tenant IDs)
- Full exception stack traces in API responses
- File system paths or internal service names

## Documentation Requirements

### README.md (Setup and Deployment)
- Project overview and architecture summary
- Prerequisites: Python 3.11+, Docker, Railway CLI, AWS account with BAA
- Local development setup: Docker Compose, environment variables, database migrations
- Deployment guide: Railway template deployment, environment configuration
- Testing instructions (once Feature 17 is implemented)

### API_ARCHITECTURE.md (Extension Points)
- Project structure explanation with component responsibilities
- Domain-based route organization pattern
- How to add new API domains (example: adding /api/v1/documents)
- Middleware execution order and how to add custom middleware
- Database connection patterns (async sessions, connection pooling)
- Error handling conventions
- Logging patterns and how to add context

### AUTH_CONFIGURATION.md (IdP Setup)
- JWT token structure and required claims (tenant_id, user_id, exp, iss)
- AWS Cognito setup guide:
  - Create user pool with MFA enabled
  - Configure app client (OIDC settings)
  - Add custom attributes for tenant_id
  - Configure hosted UI for login/logout
  - Example Lambda trigger to inject tenant_id claim
- Generic OIDC/SAML configuration for other IdPs (Okta, Auth0, Azure AD)
- Token expiration recommendations (max 60 minutes)
- Testing authentication locally with mock JWT tokens

### DEPLOYMENT.md (Railway and AWS)
- Railway template deployment step-by-step:
  - Fork repository
  - Deploy Railway template
  - Configure environment variables
  - Link PostgreSQL service
  - Connect to AWS VPC (for Feature 3)
- AWS Secrets Manager setup:
  - Create secret with OIDC_CLIENT_SECRET
  - Configure IAM role for Railway service
  - Grant secretsmanager:GetSecretValue permission
- Environment variable reference (all required variables)
- Health check endpoint configuration in Railway
- Rollback procedures

### ERROR_CODES.md (Error Registry)
- Complete list of error codes with descriptions
- AUTH_001 - AUTH_999: Authentication errors
  - AUTH_001: Invalid token (signature verification failed)
  - AUTH_002: CSRF validation failed
  - AUTH_003: Token expired
  - AUTH_004: Invalid token signature
  - AUTH_005: Missing tenant claim in JWT
  - AUTH_006: Invalid redirect URI
- SYS_001 - SYS_999: System errors
  - SYS_001: Database unreachable
  - SYS_002: Secrets Manager unavailable
  - SYS_003: Internal server error
- How to add new error codes (extend ErrorRegistry class)
- Error response format specification

### HIPAA_READINESS.md (Compliance Checklist)

Comprehensive HIPAA readiness checklist covering all HIPAA Security Rule requirements. This is a documentation reference only - not all items are implemented in this feature.

**Access Control (§164.312(a))**
- [x] Unique User Identification: Implemented via IdP (OIDC/SAML with user_id claim)
- [ ] Emergency Access Procedure: Document emergency access procedures (Feature 13)
- [ ] Automatic Logoff: Implement session timeout (documented as stretch goal)
- [ ] Encryption and Decryption: Implement per-tenant encryption (Feature 4)
- [x] Role-Based Access Control: Document RBAC architecture (Feature 13 implements)

**Audit Controls (§164.312(b))**
- [x] Audit Events Documentation: Documented audit events for future implementation
- [x] Request ID Tracing: Implemented with request_id in logs
- [x] User Context Logging: Implemented with user_id and tenant_id in logs
- [ ] Immutable Audit Logs: Implement append-only audit table (Feature 10)
- [ ] Log Retention: Configure 6-10 year retention (Feature 10)

**Integrity (§164.312(c))**
- [x] Data Transmission Security: TLS 1.2+ enforced
- [ ] Data Integrity Validation: Implement checksums for documents (Feature 5)

**Person or Entity Authentication (§164.312(d))**
- [x] Authentication Mechanism: JWT-based authentication with IdP
- [x] Multi-Factor Authentication: MFA enforced at IdP level
- [x] Token Expiration: Maximum 60-minute token lifetime

**Transmission Security (§164.312(e))**
- [x] Integrity Controls: TLS 1.2+ for all connections
- [x] Encryption: TLS for data in transit
- [ ] VPC Network Segmentation: Configure VPC with private subnets (Feature 3)

**Administrative Safeguards**
- [ ] Security Management Process: Document security policies
- [ ] Workforce Training: Document training requirements
- [ ] Contingency Plan: Document backup and disaster recovery (Feature 3)

**Physical Safeguards**
- [x] Facility Access Controls: Managed by AWS/Railway (BAA coverage)
- [x] Workstation Security: Developer workstation security guidelines (in README)

**Technical Safeguards (Additional)**
- [x] Access Logging: Request logging with user context
- [ ] Encryption Key Management: Per-tenant KMS keys (Feature 4)
- [ ] Data Backup: RDS automated backups (Feature 3)
- [ ] Disaster Recovery: Multi-AZ RDS deployment (Feature 3)

**Business Associate Agreements**
- [x] AWS BAA: Document required AWS services (RDS, S3, KMS, Bedrock)
- [x] Railway BAA: Document Railway BAA requirement
- [ ] IdP BAA: Document IdP BAA requirement (e.g., AWS Cognito, Okta)

**Compliance Artifacts**
- Security policies and procedures documentation
- Incident response plan template
- Data breach notification procedures
- Risk assessment template
- Penetration testing recommendations

## Out of Scope

**Explicitly Excluded from This Feature:**

Authentication & Access Control (Future Features)
- User management CRUD operations (create, update, delete users)
- Password reset and forgot password flows
- MFA configuration UI (MFA enforced at IdP level, not in application)
- Session management and refresh token implementation
- Token refresh endpoints
- API key management for service-to-service authentication
- User invitation and onboarding flows
- Password complexity policies and validation
- Account lockout mechanisms after failed login attempts

Authorization (Feature 13)
- Role-Based Access Control (RBAC) implementation
- Permission checks on API endpoints
- Role assignment and management
- Tenant admin roles and delegation

Application Features (Future Features)
- Document ingestion endpoints (Feature 5)
- Document storage and metadata (Feature 5)
- RAG search endpoints (Features 8-9)
- Embedding generation (Feature 7)
- Actual audit log table and implementation (Feature 10)
- Admin dashboard UI (Feature 12)

Infrastructure (Feature 3)
- AWS VPC creation and configuration
- RDS PostgreSQL instance provisioning
- S3 bucket creation with encryption
- KMS key management and rotation
- Security groups and network ACLs

Rate Limiting & Performance
- Rate limiting middleware (IP-based or user-based)
- Request throttling
- API usage quotas per tenant
- Caching layer (Redis/ElastiCache)

## Success Criteria

**Deployment Success**
- Railway template deploys successfully with one-click provisioning
- Health check endpoints return 200 OK within 1 minute of deployment
- Database connection established with pgvector extension enabled
- Application logs appear in Railway/CloudWatch

**Authentication Success**
- JWT tokens from AWS Cognito validate successfully
- Tenant ID extracted from JWT custom claim
- Authenticated requests include tenant context
- Authentication failures return appropriate error codes

**Developer Experience**
- Local development environment runs with Docker Compose
- .env.example provides clear setup instructions
- Documentation enables new developer to deploy in under 1 hour
- Code passes pre-commit hooks (black, ruff, mypy)

**Compliance Readiness**
- All logging follows HIPAA practices (no PHI in logs)
- TLS 1.2+ enforced for all connections
- Structured audit events documented for future implementation
- HIPAA_READINESS.md checklist complete

**Architecture Quality**
- Domain-based route structure clearly defined
- Extension points documented for future features
- Middleware patterns reusable for additional context extraction
- Error handling patterns consistent across all endpoints

**Performance**
- Health check latency < 100ms
- Authentication request latency < 500ms
- JWKS key caching reduces validation latency (< 50ms cache hits)
- Database connection pool handles 20 concurrent requests

## Extension Points for Template Users

**Adding New API Domains**
- Create new router in app/api/v1/{domain}.py
- Register router in app/main.py
- Follow domain-based naming convention
- Use tenant context from request.state.tenant_id

**Adding Custom Middleware**
- Create middleware in app/middleware/{name}.py
- Register in app/main.py middleware stack
- Middleware execution order: logging → tenant context → auth → custom
- Access tenant context via request.state

**Adding New Error Codes**
- Extend ErrorRegistry in app/utils/errors.py
- Follow naming convention: {DOMAIN}_{NUMBER} (e.g., DOC_001)
- Document in docs/ERROR_CODES.md
- Use in exception handling

**Extending Authentication**
- Custom JWT claim extraction in TenantExtractor
- Additional IdP configuration in app/config.py
- Support for multiple tenant claim names (configurable priority)

**Adding Audit Events** (for Feature 10)
- Use documented audit event types in HIPAA_READINESS.md
- Extend with domain-specific events
- Follow structured format: event_type, user_id, tenant_id, resource_type, resource_id

## Dependencies & Prerequisites

**AWS Services (BAA Required)**
- RDS PostgreSQL 15+ with BAA coverage (Feature 3 provisions)
- AWS KMS for key management (Feature 4 provisions)
- AWS Secrets Manager for runtime secrets (Feature 3 provisions)
- AWS CloudWatch for log aggregation (Railway auto-configures)

**Railway Configuration**
- Railway account with HIPAA BAA signed
- Railway project with PostgreSQL service linked
- Railway environment variables configured
- Railway CLI installed for local deployment

**Identity Provider Setup**
- IdP supporting OIDC or SAML (AWS Cognito, Okta, Auth0, Azure AD)
- IdP BAA signed (required for HIPAA compliance)
- Custom JWT claim configured for tenant_id
- MFA enabled at IdP level
- JWKS endpoint publicly accessible

**Development Tools**
- Python 3.11+
- Docker and Docker Compose
- uv package manager (installed via pip or curl)
- Git for version control

**Local Development Prerequisites**
- PostgreSQL 15+ with pgvector extension (via Docker Compose)
- Environment variables configured in .env file
- AWS credentials for Secrets Manager access (optional for local dev)

## Stretch Goals (Documented for Future Features)

These are explicitly out of scope for this feature but should be documented as future extension points:

**Session Management** (Potential Feature 19)
- Refresh token implementation with rotation
- Session storage (Redis or database)
- Token revocation on logout
- Remember me functionality

**Advanced Authentication** (Potential Feature 20)
- API key authentication for service accounts
- Webhook signature validation
- OAuth2 client credentials flow
- SAML assertion validation

**Rate Limiting** (Potential Feature 21)
- Per-user request rate limits
- Per-tenant API quotas
- Distributed rate limiting with Redis
- Rate limit headers in responses

**Enhanced Security** (Potential Feature 22)
- CSRF token validation for stateful sessions
- Request signing for API clients
- IP allowlisting per tenant
- Anomaly detection for suspicious authentication patterns

**User Management** (Potential Feature 23)
- User CRUD APIs with tenant scoping
- User profile management
- User search and filtering
- User invitation and onboarding workflows

Documentation should reference these stretch goals as "Future Enhancements" with links to potential feature specs.
