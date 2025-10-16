# Task Breakdown: Backend API Scaffold with Authentication

## Overview

**Total Tasks:** 38 tasks across 10 phases
**Estimated Total Effort:** 6-10 days (48-80 hours)
**Assigned Implementers:** database-engineer, api-engineer, testing-engineer

## Critical Path Summary

The critical path flows sequentially through phases 1-10:
1. Project setup establishes foundation
2. Database setup enables data persistence
3. Configuration enables environment-based settings
4. Authentication core implements JWT validation
5. Middleware implements tenant isolation
6. API endpoints expose functionality
7. Error handling standardizes responses
8. Deployment configuration enables Railway deployment
9. Documentation enables developer onboarding
10. Testing validates critical workflows

**Key Dependencies:**
- Phases 1-2 are foundational and block all other work
- Phase 3 (configuration) blocks authentication and middleware
- Phase 4 (authentication) blocks API endpoints
- Phase 5 (middleware) blocks API endpoints
- Phases 6-7 can partially overlap
- Phase 8 (deployment) requires phases 1-7 complete
- Phase 9 (documentation) can start early but finalizes at end
- Phase 10 (testing) validates everything

---

## Phase 1: Project Setup & Foundation

**Phase Goal:** Establish FastAPI project structure, dependencies, and basic application skeleton

### Task Group 1: FastAPI Project Initialization
**Assigned implementer:** api-engineer
**Dependencies:** None

- [x] 1.0 Initialize FastAPI project structure and dependencies
  - [x] 1.1 Create project directory structure
    - Create `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/` directory
    - Create subdirectories: `app/`, `app/api/`, `app/api/v1/`, `app/auth/`, `app/middleware/`, `app/database/`, `app/models/`, `app/utils/`, `alembic/`, `tests/`, `scripts/`
    - Create `__init__.py` files in all Python package directories
  - [x] 1.2 Configure uv package manager and dependencies
    - Create `backend/pyproject.toml` with project metadata
    - Add core dependencies: fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, python-jose[cryptography], httpx, python-multipart
    - Add development dependencies: ruff, black, mypy, pytest, pytest-asyncio
    - Configure tool settings for ruff, black, mypy in pyproject.toml
  - [x] 1.3 Create FastAPI application factory
    - Create `backend/app/main.py` with FastAPI app initialization
    - Configure app metadata (title, description, version)
    - Set up basic CORS middleware with placeholder origins
    - Add OpenAPI configuration
    - Create root endpoint returning `{"status": "ok"}`
  - [x] 1.4 Verify FastAPI application starts
    - Test that `uvicorn app.main:app --reload` starts successfully
    - Verify root endpoint responds with 200 OK
    - Verify OpenAPI docs accessible at `/docs`

**Deliverables:**
- `backend/pyproject.toml` (dependency configuration)
- `backend/app/main.py` (FastAPI app factory)
- Complete directory structure with `__init__.py` files

**Acceptance Criteria:**
- FastAPI app starts without errors
- Root endpoint returns `{"status": "ok"}`
- OpenAPI docs render at `/docs`
- `uv sync` installs all dependencies successfully

**Effort:** M (4-6 hours)

---

## Phase 2: Database Foundation

**Phase Goal:** Set up SQLAlchemy async engine, connection pooling, and Alembic migrations

### Task Group 2: Database Engine & Migrations
**Assigned implementer:** database-engineer
**Dependencies:** Task Group 1

- [x] 2.0 Configure database engine and migration framework
  - [x] 2.1 Create SQLAlchemy async engine setup
    - Create `backend/app/database/engine.py`
    - Configure async engine factory with connection pooling (pool_size=10, max_overflow=10, pool_timeout=30, pool_pre_ping=True)
    - Implement connection retry logic with exponential backoff (max 3 retries)
    - Add database URL validation
    - Create async session factory with proper lifecycle management
  - [x] 2.2 Create declarative base model
    - Create `backend/app/database/base.py`
    - Define SQLAlchemy DeclarativeBase
    - Add common fields: `id` (UUID primary key), `created_at`, `updated_at`
    - Configure automatic timestamp updates
  - [x] 2.3 Initialize Alembic migration framework
    - Run `alembic init alembic` in backend directory
    - Configure `backend/alembic.ini` with database URL placeholder
    - Update `backend/alembic/env.py` to use async engine
    - Import DeclarativeBase metadata for auto-detection
    - Configure Alembic to load DATABASE_URL from environment
  - [x] 2.4 Create initial migration for pgvector extension
    - Create migration: `alembic revision -m "enable_pgvector_extension"`
    - Add upgrade: `CREATE EXTENSION IF NOT EXISTS vector;`
    - Add downgrade: `DROP EXTENSION IF EXISTS vector;`
    - Add comment documenting future tables (tenant, user, document)
  - [x] 2.5 Verify database connection and migrations
    - Test database engine connection with test DATABASE_URL
    - Run `alembic upgrade head` successfully
    - Verify pgvector extension enabled in PostgreSQL
    - Test connection pool handles concurrent connections

**Deliverables:**
- `backend/app/database/engine.py` (async engine with connection pooling)
- `backend/app/database/base.py` (declarative base model)
- `backend/alembic.ini` (Alembic configuration)
- `backend/alembic/env.py` (async Alembic environment)
- `backend/alembic/versions/001_enable_pgvector_extension.py` (initial migration)

**Acceptance Criteria:**
- Database engine connects successfully with async connection
- Connection pool maintains 10-20 connections under load
- Connection retry logic recovers from transient failures
- Alembic migration runs and enables pgvector extension
- No tables created yet (Feature 2 will add tables)

**Effort:** M (5-7 hours)

---

## Phase 3: Configuration Management

**Phase Goal:** Set up environment variable management, AWS Secrets Manager integration, and Pydantic settings

### Task Group 3: Configuration & Secrets Management
**Assigned implementer:** api-engineer
**Dependencies:** Task Groups 1-2

- [x] 3.0 Implement configuration and secrets management
  - [x] 3.1 Create Pydantic settings model
    - Create `backend/app/config.py`
    - Define Settings class inheriting from BaseSettings
    - Add environment-based settings: ENVIRONMENT, LOG_LEVEL, ALLOWED_ORIGINS, DATABASE_URL
    - Add authentication settings: OIDC_ISSUER_URL, OIDC_CLIENT_ID, JWT_TENANT_CLAIM_NAME, JWT_MAX_LIFETIME_MINUTES
    - Add AWS settings: AWS_REGION, AWS_SECRETS_MANAGER_SECRET_ID
    - Configure field validation (URL formats, allowed values)
    - Add settings caching with @lru_cache
  - [x] 3.2 Implement AWS Secrets Manager client
    - Create `backend/app/utils/secrets_manager.py`
    - Implement async AWS Secrets Manager client using boto3/aioboto3
    - Add secret fetching with retry logic (3 retries, exponential backoff)
    - Cache secrets in memory (no disk writes)
    - Handle IAM role authentication for Railway environment
    - Add graceful fallback for local development (skip if AWS credentials unavailable)
  - [x] 3.3 Integrate secrets into settings
    - Update Settings class to fetch OIDC_CLIENT_SECRET from Secrets Manager on startup
    - Add initialization method to load runtime secrets
    - Handle secret loading errors gracefully (log warning, don't crash)
    - Document which secrets come from env vars vs Secrets Manager
  - [x] 3.4 Create environment variable templates
    - Create `backend/.env.example` with all required variables and inline documentation
    - Document local development values (localhost origins, test database URL)
    - Add comments explaining each variable's purpose
    - Mark which variables are required vs optional
    - Document AWS Secrets Manager integration pattern
  - [x] 3.5 Verify configuration loading
    - Test settings load from .env file successfully
    - Test settings validation catches invalid values
    - Test AWS Secrets Manager integration (mock for local dev)
    - Verify settings accessible throughout application

**Deliverables:**
- `backend/app/config.py` (Pydantic settings model)
- `backend/app/utils/secrets_manager.py` (AWS Secrets Manager client)
- `backend/.env.example` (environment variable template)

**Acceptance Criteria:**
- Settings load from environment variables successfully
- Settings validation catches invalid configurations
- AWS Secrets Manager client fetches secrets with retry logic
- Application gracefully handles missing AWS credentials in local dev
- .env.example documents all required variables with clear descriptions

**Effort:** M (5-7 hours)

---

## Phase 4: Authentication Core

**Phase Goal:** Implement JWT validation, JWKS caching, and tenant extraction

### Task Group 4: JWT Validation & JWKS Integration
**Assigned implementer:** api-engineer
**Dependencies:** Task Group 3

- [x] 4.0 Implement JWT validation and JWKS integration
  - [x] 4.1 Create JWKS key cache
    - Create `backend/app/auth/jwks_cache.py`
    - Implement in-memory JWKS key cache with TTL (1 hour default, configurable)
    - Add background refresh before TTL expiration to prevent cache miss latency
    - Implement async JWKS fetching from OIDC issuer's .well-known/jwks.json endpoint using httpx
    - Add retry logic for JWKS fetch failures (3 retries, exponential backoff)
    - Cache keys by key ID (kid) for fast lookup
  - [x] 4.2 Implement JWT validator
    - Create `backend/app/auth/jwt_validator.py`
    - Implement JWTValidator class with signature verification using python-jose
    - Parse JWT header to extract key ID (kid)
    - Fetch public key from JWKS cache (trigger fetch if cache miss)
    - Verify JWT signature using RSA public key
    - Validate standard claims: exp (expiration), iat (issued at), iss (issuer), aud (audience)
    - Enforce token expiration < JWT_MAX_LIFETIME_MINUTES (60 minutes default)
    - Return decoded JWT claims dictionary
    - Raise specific exceptions for different validation failures
  - [x] 4.3 Create tenant extractor
    - Create `backend/app/auth/tenant_extractor.py`
    - Implement TenantExtractor class to parse tenant_id from JWT claims
    - Support configurable claim names (tenant_id, organization_id) with priority order
    - Validate tenant_id format (e.g., "org-{uuid}" pattern)
    - Raise exception if tenant_id claim missing
    - Return validated tenant_id string
  - [x] 4.4 Create FastAPI authentication dependencies
    - Create `backend/app/auth/dependencies.py`
    - Implement `get_current_user` dependency extracting JWT from Authorization header
    - Validate JWT using JWTValidator
    - Extract tenant_id using TenantExtractor
    - Return user context dictionary: {user_id, tenant_id, claims}
    - Handle authentication errors with appropriate HTTP exceptions
  - [x] 4.5 Verify JWT validation flow
    - Test JWKS fetch and caching works correctly
    - Test JWT signature verification with valid/invalid tokens
    - Test claim validation (expiration, issuer, audience)
    - Test tenant extraction with various claim configurations
    - Test error handling for missing/invalid tokens

**Deliverables:**
- `backend/app/auth/jwks_cache.py` (JWKS key cache with TTL)
- `backend/app/auth/jwt_validator.py` (JWT signature and claim validation)
- `backend/app/auth/tenant_extractor.py` (tenant_id extraction from claims)
- `backend/app/auth/dependencies.py` (FastAPI authentication dependencies)

**Acceptance Criteria:**
- JWKS keys fetched and cached successfully with 1-hour TTL
- JWT signature verification works with cached public keys
- Standard JWT claims validated correctly (exp, iat, iss, aud)
- Token expiration enforced (max 60 minutes lifetime)
- Tenant ID extracted from configurable JWT claim
- Authentication errors return appropriate HTTP 401/403 responses

**Effort:** L (8-10 hours)

---

## Phase 5: Middleware Layer

**Phase Goal:** Implement tenant context, logging, and exception handling middleware

### Task Group 5: Middleware Implementation
**Assigned implementer:** api-engineer
**Dependencies:** Task Group 4

- [x] 5.0 Implement middleware for tenant context, logging, and error handling
  - [x] 5.1 Create tenant context middleware
    - Create `backend/app/middleware/tenant_context.py`
    - Implement middleware extracting tenant_id from authenticated request state
    - Inject tenant_id into request.state for downstream access
    - Validate tenant_id exists (fail request if missing after authentication)
    - Add tenant_id to logging context
    - Return 403 Forbidden if tenant claim missing with error code AUTH_005
  - [x] 5.2 Create logging middleware
    - Create `backend/app/middleware/logging.py`
    - Generate unique request_id (UUID4) at request start
    - Inject request_id, tenant_id, user_id into logging context
    - Log request start (DEBUG level): method, path, query params (sanitized)
    - Log request completion (INFO level): status code, duration_ms, error if failed
    - Redact sensitive data: Authorization headers, password fields, PHI in query params
    - Add request_id to response headers for client correlation
  - [x] 5.3 Create exception handling middleware
    - Create `backend/app/middleware/exception.py`
    - Catch all unhandled exceptions
    - Convert exceptions to standardized error response format
    - Log exception with full stack trace (ERROR level)
    - Return appropriate HTTP status codes
    - Never expose stack traces to clients (only in logs)
    - Add request_id to error response for correlation
  - [x] 5.4 Configure structured JSON logging
    - Create `backend/app/utils/logger.py`
    - Configure Python logging to output structured JSON
    - Define JSON log format: timestamp, level, logger, message, request_id, user_id, tenant_id, context
    - Set up log levels by environment (DEBUG for development, INFO for production)
    - Output to stdout for Railway CloudWatch integration
    - Add context manager for enriching log records
  - [x] 5.5 Register middleware in FastAPI app
    - Update `backend/app/main.py` to register middleware
    - Configure middleware execution order: logging -> exception -> tenant context -> auth
    - Verify middleware applies to all routes
    - Test middleware chain executes correctly

**Deliverables:**
- `backend/app/middleware/tenant_context.py` (tenant isolation middleware)
- `backend/app/middleware/logging.py` (request/response logging)
- `backend/app/middleware/exception.py` (exception handling)
- `backend/app/utils/logger.py` (structured JSON logging setup)

**Acceptance Criteria:**
- Tenant context middleware extracts and validates tenant_id from JWT
- Request logging includes request_id, tenant_id, user_id in structured JSON
- All logs output to stdout in JSON format
- Exception middleware catches all errors and returns standardized responses
- Sensitive data redacted from logs (no Authorization headers, no PHI)
- Middleware execution order correct

**Effort:** L (7-9 hours)

---

## Phase 6: API Endpoints

**Phase Goal:** Implement authentication and health check endpoints

### Task Group 6: Authentication Endpoints
**Assigned implementer:** api-engineer
**Dependencies:** Task Groups 4-5

- [x] 6.0 Implement authentication API endpoints
  - [x] 6.1 Create authentication router
    - Create `backend/app/api/v1/auth.py`
    - Set up FastAPI router with `/api/v1/auth` prefix
    - Import authentication dependencies
  - [x] 6.2 Implement POST /api/v1/auth/callback endpoint
    - Handle IdP callback after successful authentication
    - Request body: `{"code": "auth_code", "state": "csrf_token"}`
    - Exchange auth code for JWT token at IdP token endpoint
    - Validate CSRF state parameter
    - Return access token: `{"access_token": "jwt_token", "token_type": "Bearer", "expires_in": 3600}`
    - Handle errors: AUTH_001 (Invalid code), AUTH_002 (CSRF validation failed)
  - [x] 6.3 Implement GET /api/v1/auth/validate endpoint
    - Validate current user's JWT token
    - Require Authorization header: `Bearer <token>`
    - Use get_current_user dependency for validation
    - Return validation result: `{"valid": true, "user_id": "123", "tenant_id": "org-456", "expires_at": 1234567890}`
    - Handle errors: AUTH_003 (Token expired), AUTH_004 (Invalid signature), AUTH_005 (Missing tenant claim)
  - [x] 6.4 Implement POST /api/v1/auth/logout endpoint
    - Invalidate session via IdP logout redirect
    - Request body: `{"redirect_uri": "https://app.example.com"}`
    - Validate redirect URI against allowed origins
    - Generate IdP logout URL with redirect
    - Return logout URL: `{"logout_url": "https://idp.example.com/logout?..."}`
    - Handle errors: AUTH_006 (Invalid redirect URI)
  - [x] 6.5 Verify authentication endpoints
    - Test callback endpoint with mock auth code
    - Test validate endpoint with valid/invalid JWT
    - Test logout endpoint with valid/invalid redirect URI
    - Verify error responses match standardized format
    - Verify tenant context available in request state

**Deliverables:**
- `backend/app/api/v1/auth.py` (authentication endpoints)

**Acceptance Criteria:**
- POST /api/v1/auth/callback exchanges auth code for JWT
- GET /api/v1/auth/validate returns user and tenant context
- POST /api/v1/auth/logout returns IdP logout URL
- All endpoints return standardized error format
- Authentication errors use correct error codes (AUTH_001-006)

**Effort:** L (7-9 hours)

### Task Group 7: Health Check Endpoints
**Assigned implementer:** api-engineer
**Dependencies:** Task Group 2

- [x] 7.0 Implement health check API endpoints
  - [x] 7.1 Create health check router
    - Create `backend/app/api/v1/health.py`
    - Set up FastAPI router with `/api/v1/health` prefix
    - Import database engine for connectivity checks
  - [x] 7.2 Implement GET /api/v1/health/live endpoint
    - Kubernetes-style liveness probe
    - Always return 200 OK unless application crashed
    - Response: `{"status": "ok", "timestamp": 1234567890}`
    - Target response time: < 100ms
    - No external dependency checks
  - [x] 7.3 Implement GET /api/v1/health/ready endpoint
    - Kubernetes-style readiness probe with dependency checks
    - Check database connectivity (execute simple query)
    - Check AWS Secrets Manager availability (optional, log warning if unavailable)
    - Response: `{"status": "ready", "checks": {"database": "ok", "secrets": "ok"}, "timestamp": 1234567890}`
    - Return 503 Service Unavailable if dependencies down
    - Errors: SYS_001 (Database unreachable), SYS_002 (Secrets Manager unavailable)
    - Target response time: < 500ms
  - [x] 7.4 Register health router in main app
    - Update `backend/app/main.py` to include health router
    - Configure router prefix and tags
  - [x] 7.5 Verify health check endpoints
    - Test liveness endpoint returns 200 OK quickly (< 100ms)
    - Test readiness endpoint checks database connectivity
    - Test readiness endpoint returns 503 when database unavailable
    - Verify health checks don't require authentication

**Deliverables:**
- `backend/app/api/v1/health.py` (health check endpoints)

**Acceptance Criteria:**
- GET /api/v1/health/live returns 200 OK in < 100ms
- GET /api/v1/health/ready validates database connectivity
- Readiness check returns 503 if dependencies unavailable
- Health checks accessible without authentication
- Readiness check includes timestamp and dependency statuses

**Effort:** S (3-4 hours)

---

## Phase 7: Error Handling & CORS

**Phase Goal:** Standardize error responses and configure CORS

### Task Group 8: Error Registry & Response Format
**Assigned implementer:** api-engineer
**Dependencies:** Task Group 1

- [x] 8.0 Create error registry and standardized error handling
  - [x] 8.1 Create error code registry
    - Create `backend/app/utils/errors.py`
    - Define ErrorRegistry class with error code constants
    - Add authentication error codes: AUTH_001 through AUTH_006
    - Add system error codes: SYS_001 through SYS_003
    - Add validation error codes: VAL_001 through VAL_999 (placeholders for future)
    - Document error code meanings with inline comments
  - [x] 8.2 Create custom exception classes
    - Define base APIException class with error_code, message, detail, status_code
    - Create specific exception classes: AuthenticationError, AuthorizationError, ValidationError, SystemError
    - Configure exception to error code mapping
  - [x] 8.3 Implement standardized error response formatter
    - Create format_error_response function
    - Generate error response: `{"error": {"code": "AUTH_001", "message": "Invalid token", "detail": "...", "request_id": "..."}}`
    - Include request_id from logging context
    - Never include stack traces in response
  - [x] 8.4 Update exception middleware to use error registry
    - Modify `backend/app/middleware/exception.py` to use ErrorRegistry
    - Map Python exceptions to API error codes
    - Use format_error_response for all errors
    - Log full exception details while returning safe client messages
  - [x] 8.5 Verify error handling
    - Test custom exceptions return correct error codes
    - Test unhandled exceptions return SYS_003 (Internal server error)
    - Verify error responses include request_id
    - Verify stack traces not exposed to clients
    - Verify error details logged but not returned to client

**Deliverables:**
- `backend/app/utils/errors.py` (error registry and custom exceptions)

**Acceptance Criteria:**
- All error codes documented with descriptions
- Error responses follow standardized format
- Exception middleware maps all exceptions to error codes
- Stack traces logged but never exposed to clients
- Request ID included in all error responses

**Effort:** M (4-5 hours)

### Task Group 9: CORS Configuration
**Assigned implementer:** api-engineer
**Dependencies:** Task Group 3

- [x] 9.0 Configure CORS with environment-based origins
  - [x] 9.1 Update CORS middleware configuration
    - Update `backend/app/main.py` CORS middleware
    - Load allowed origins from Settings.ALLOWED_ORIGINS
    - Parse comma-separated origin list from environment variable
    - Set allow_credentials=True for cookie-based refresh tokens
    - Configure allowed methods: GET, POST, PUT, DELETE, OPTIONS
    - Configure allowed headers: Authorization, Content-Type
    - Set Access-Control-Max-Age to 86400 (24 hours)
  - [x] 9.2 Set development defaults in .env.example
    - Add ALLOWED_ORIGINS with localhost defaults: http://localhost:3000,http://localhost:5173,http://localhost:8080
    - Document CORS configuration for production (no wildcards with credentials)
  - [ ] 9.3 Verify CORS configuration
    - Test preflight OPTIONS requests return correct headers
    - Test credentials allowed with explicit origins
    - Verify wildcards rejected when credentials enabled
    - Test multiple origins parsed correctly from env var

**Deliverables:**
- Updated `backend/app/main.py` (CORS middleware configuration)
- Updated `backend/.env.example` (CORS environment variable)

**Acceptance Criteria:**
- CORS allows configured origins from environment variable
- Credentials enabled for cookie-based authentication
- Preflight requests handled correctly
- Development defaults include common localhost ports
- Production requires explicit origin configuration

**Effort:** S (2-3 hours)

---

## Phase 8: Deployment Configuration

**Phase Goal:** Create Docker, Railway, and deployment scripts

### Task Group 10: Docker & Railway Configuration
**Assigned implementer:** api-engineer
**Dependencies:** Task Groups 1-7

- [x] 10.0 Create deployment configuration for Railway
  - [x] 10.1 Create multi-stage Dockerfile
    - Create `backend/Dockerfile`
    - Stage 1 (builder): Install uv, copy pyproject.toml, run uv sync --frozen
    - Stage 2 (runtime): Copy .venv from builder, copy app code and alembic
    - Configure Python 3.11-slim base image
    - Set working directory to /app
    - Expose port 8000
    - Set CMD to startup script
  - [x] 10.2 Create startup script with automatic migrations
    - Create `backend/scripts/startup.sh`
    - Add shebang and set -e for error exit
    - Run `alembic upgrade head` before starting app
    - Start uvicorn: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
    - Add logging for migration and startup steps
  - [x] 10.3 Create railway.json configuration
    - Create `backend/railway.json`
    - Configure builder: DOCKERFILE
    - Set dockerfilePath: Dockerfile
    - Configure deploy: startCommand pointing to startup script
    - Set restartPolicyType: ON_FAILURE with maxRetries: 3
    - Configure healthcheckPath: /api/v1/health/ready
    - Set healthcheckTimeout: 30
  - [x] 10.4 Create .dockerignore
    - Create `backend/.dockerignore`
    - Exclude: .env, .venv, __pycache__, *.pyc, .git, tests/, .mypy_cache/, .pytest_cache/
  - [x] 10.5 Verify Docker build and Railway configuration
    - Test Docker build completes successfully
    - Test Docker container starts and runs migrations
    - Verify health check endpoint accessible in container
    - Validate railway.json configuration syntax

**Deliverables:**
- `backend/Dockerfile` (multi-stage production build)
- `backend/scripts/startup.sh` (migration and startup script)
- `backend/railway.json` (Railway deployment configuration)
- `backend/.dockerignore` (Docker build exclusions)

**Acceptance Criteria:**
- Docker image builds successfully with multi-stage optimization
- Startup script runs Alembic migrations before app start
- Container exposes health check endpoint on port 8000
- Railway configuration valid and ready for deployment
- Docker build excludes development files (.env, tests, caches)

**Effort:** M (4-5 hours)

---

## Phase 9: Documentation

**Phase Goal:** Create comprehensive documentation for setup, deployment, and extension

### Task Group 11: Setup & Deployment Documentation
**Assigned implementer:** api-engineer
**Dependencies:** Task Groups 1-10

- [x] 11.0 Create comprehensive project documentation
  - [x] 11.1 Create README.md
    - Create `backend/README.md`
    - Add project overview and architecture summary
    - Document prerequisites: Python 3.11+, Docker, Railway CLI, AWS account with BAA
    - Add local development setup: Install dependencies with uv, configure .env file, run Docker Compose for PostgreSQL
    - Document database migrations: `alembic upgrade head`
    - Add Railway deployment instructions: Deploy template, configure env vars, link PostgreSQL
    - Reference other documentation files
    - Add quickstart guide (< 5 minutes to running locally)
  - [x] 11.2 Create API_ARCHITECTURE.md
    - Create `backend/docs/API_ARCHITECTURE.md`
    - Explain project structure with component responsibilities
    - Document domain-based route organization pattern (/api/v1/{domain}/*)
    - Show how to add new API domains with example code
    - Explain middleware execution order and custom middleware addition
    - Document database connection patterns (async sessions, connection pooling)
    - Explain error handling conventions and error code usage
    - Document logging patterns and context injection
    - Show future extension points for documents, RAG endpoints
  - [x] 11.3 Create AUTH_CONFIGURATION.md
    - Create `backend/docs/AUTH_CONFIGURATION.md`
    - Document required JWT token structure and claims (tenant_id, user_id, exp, iss, aud)
    - Provide AWS Cognito setup guide: Create user pool with MFA, configure app client, add custom tenant_id attribute, configure hosted UI, example Lambda trigger for claim injection
    - Document generic OIDC/SAML configuration for Okta, Auth0, Azure AD
    - Add token expiration recommendations (max 60 minutes)
    - Show how to test authentication locally with mock JWT tokens
    - Document JWKS endpoint configuration
  - [x] 11.4 Create DEPLOYMENT.md
    - Create `backend/docs/DEPLOYMENT.md`
    - Provide Railway template deployment step-by-step: Fork repo, deploy template, configure env vars, link PostgreSQL service
    - Document AWS Secrets Manager setup: Create secret, configure IAM role, grant permissions
    - Add environment variable reference table (all required variables)
    - Document health check endpoint configuration in Railway
    - Add rollback procedures
    - Document manual migration execution for template users
  - [x] 11.5 Create ERROR_CODES.md
    - Create `backend/docs/ERROR_CODES.md`
    - Document complete error code registry with descriptions
    - Add AUTH_001 through AUTH_006 (authentication errors)
    - Add SYS_001 through SYS_003 (system errors)
    - Add VAL_001 through VAL_999 (validation errors, placeholders)
    - Show how to add new error codes (extend ErrorRegistry)
    - Document error response format specification
    - Provide troubleshooting guide for common errors

**Deliverables:**
- `backend/README.md` (setup and deployment overview)
- `backend/docs/API_ARCHITECTURE.md` (extension points and patterns)
- `backend/docs/AUTH_CONFIGURATION.md` (IdP setup guides)
- `backend/docs/DEPLOYMENT.md` (Railway and AWS deployment)
- `backend/docs/ERROR_CODES.md` (error registry documentation)

**Acceptance Criteria:**
- README enables new developer to set up locally in < 1 hour
- API_ARCHITECTURE clearly shows how to add new domains
- AUTH_CONFIGURATION provides working AWS Cognito setup
- DEPLOYMENT covers both Railway and AWS configuration
- ERROR_CODES documents all error codes with troubleshooting

**Effort:** L (8-10 hours)

### Task Group 12: HIPAA Compliance Documentation
**Assigned implementer:** api-engineer
**Dependencies:** Task Groups 1-10

- [x] 12.0 Create HIPAA readiness documentation
  - [x] 12.1 Create HIPAA_READINESS.md
    - Create `backend/docs/HIPAA_READINESS.md`
    - Add comprehensive HIPAA Security Rule checklist
    - Document Access Control (164.312(a)): Unique user identification (implemented), emergency access (future), automatic logoff (future), encryption (future), RBAC (future)
    - Document Audit Controls (164.312(b)): Audit events (documented), request ID tracing (implemented), user context logging (implemented), immutable logs (future), retention (future)
    - Document Integrity (164.312(c)): Transmission security (implemented), data integrity validation (future)
    - Document Person/Entity Authentication (164.312(d)): JWT authentication (implemented), MFA (IdP level), token expiration (implemented)
    - Document Transmission Security (164.312(e)): TLS 1.2+ (implemented), VPC segmentation (future)
    - Add Administrative Safeguards section (future)
    - Add Physical Safeguards section (AWS/Railway managed)
    - Document Business Associate Agreements: AWS BAA, Railway BAA, IdP BAA requirements
    - Add compliance artifacts checklist: Security policies, incident response, data breach notification, risk assessment, penetration testing
  - [x] 12.2 Document HIPAA audit events for future implementation
    - Add audit event types to HIPAA_READINESS.md
    - Document AUTH_LOGIN_SUCCESS, AUTH_LOGIN_FAILED, AUTH_LOGOUT events
    - Document AUTH_TOKEN_EXPIRED, AUTH_PERMISSION_DENIED events
    - Document DATA_ACCESS, DATA_MODIFIED events for future implementation
    - Specify event structure: event_type, user_id, tenant_id, resource_type, resource_id, timestamp, outcome
  - [x] 12.3 Document HIPAA logging practices
    - Add logging practices section to HIPAA_READINESS.md
    - Document what to log: Auth events, request metadata, user context, errors
    - Document what NOT to log: Authorization headers, PHI in query params, request/response bodies with PHI, passwords, full stack traces to external systems
    - Document log sanitization: Redact auth headers, redact sensitive query params, use reference IDs only
  - [x] 12.4 Verify HIPAA documentation completeness
    - Review all HIPAA Security Rule requirements covered
    - Verify implemented features marked correctly
    - Verify future features clearly documented
    - Cross-reference with spec requirements

**Deliverables:**
- `backend/docs/HIPAA_READINESS.md` (comprehensive HIPAA checklist)

**Acceptance Criteria:**
- All HIPAA Security Rule requirements documented
- Implemented features clearly marked as complete
- Future features documented with references to other features
- Audit event types documented for future implementation
- Logging practices documented (what to log, what NOT to log)
- BAA requirements clearly specified

**Effort:** M (5-6 hours)

### Task Group 13: Railway Environment Templates
**Assigned implementer:** api-engineer
**Dependencies:** Task Group 3

- [x] 13.0 Create Railway environment variable templates
  - [x] 13.1 Document Railway-specific environment variables
    - Create `backend/docs/RAILWAY_ENV.md`
    - List all required Railway environment variables
    - Document auto-injected variables: DATABASE_URL (from linked PostgreSQL)
    - Document user-provided variables: ENVIRONMENT, ALLOWED_ORIGINS, LOG_LEVEL
    - Document AWS configuration: AWS_REGION, AWS_SECRETS_MANAGER_SECRET_ID
    - Document authentication configuration: OIDC_ISSUER_URL, OIDC_CLIENT_ID, JWT_TENANT_CLAIM_NAME, JWT_MAX_LIFETIME_MINUTES
    - Add example values for each variable (non-sensitive)
    - Link to AWS Secrets Manager for sensitive values (OIDC_CLIENT_SECRET)
    - Document which variables are required vs optional
  - [x] 13.2 Update .env.example with Railway notes
    - Update `backend/.env.example` to include Railway deployment notes
    - Add comments indicating which variables are Railway auto-injected
    - Reference RAILWAY_ENV.md for deployment-specific configuration
  - [x] 13.3 Verify environment variable documentation
    - Cross-reference with Settings class in config.py
    - Ensure all settings documented
    - Verify example values are realistic and non-sensitive

**Deliverables:**
- `backend/docs/RAILWAY_ENV.md` (Railway environment variable guide)
- Updated `backend/.env.example` (with Railway deployment notes)

**Acceptance Criteria:**
- All Railway environment variables documented
- Auto-injected vs user-provided variables clearly distinguished
- Example values provided for all variables
- AWS Secrets Manager integration documented
- Cross-referenced with Settings class for accuracy

**Effort:** S (2-3 hours)

---

## Phase 10: Testing & Validation

**Phase Goal:** Write strategic tests covering critical authentication and health check workflows

### Task Group 14: Strategic Test Coverage
**Assigned implementer:** testing-engineer
**Dependencies:** Task Groups 1-9

- [x] 14.0 Write strategic tests for critical workflows
  - [x] 14.1 Review existing code and identify test gaps
    - Review JWT validation implementation in `backend/app/auth/jwt_validator.py`
    - Review authentication endpoints in `backend/app/api/v1/auth.py`
    - Review health check endpoints in `backend/app/api/v1/health.py`
    - Review middleware implementations in `backend/app/middleware/`
    - Identify critical user workflows needing test coverage
  - [x] 14.2 Write JWT validation tests (maximum 8 tests)
    - Create `backend/tests/test_auth/test_jwt_validator.py`
    - Test JWKS key fetching and caching
    - Test JWT signature verification with valid token
    - Test JWT signature verification with invalid token
    - Test token expiration validation
    - Test issuer validation
    - Test tenant claim extraction
    - Test handling of missing/malformed tokens
    - Test JWKS cache TTL and refresh
  - [x] 14.3 Write authentication endpoint tests (maximum 8 tests)
    - Create `backend/tests/test_api/test_auth.py`
    - Test POST /api/v1/auth/callback with valid auth code
    - Test POST /api/v1/auth/callback with invalid auth code
    - Test GET /api/v1/auth/validate with valid JWT
    - Test GET /api/v1/auth/validate with expired JWT
    - Test GET /api/v1/auth/validate with missing tenant claim
    - Test POST /api/v1/auth/logout with valid redirect URI
    - Test POST /api/v1/auth/logout with invalid redirect URI
  - [x] 14.4 Write health check endpoint tests (maximum 4 tests)
    - Create `backend/tests/test_api/test_health.py`
    - Test GET /api/v1/health/live returns 200 OK
    - Test GET /api/v1/health/ready with database available
    - Test GET /api/v1/health/ready with database unavailable
    - Test health checks don't require authentication
  - [x] 14.5 Write middleware tests (maximum 6 tests)
    - Create `backend/tests/test_middleware/test_tenant_context.py`
    - Test tenant context extraction from JWT
    - Test tenant context missing returns 403
    - Create `backend/tests/test_middleware/test_logging.py`
    - Test request ID generation and injection
    - Test structured logging output format
    - Create `backend/tests/test_middleware/test_exception.py`
    - Test exception middleware catches unhandled errors
    - Test standardized error response format
  - [x] 14.6 Create test fixtures and utilities
    - Create `backend/tests/conftest.py` with pytest fixtures
    - Add fixture for test FastAPI client
    - Add fixture for mock JWT tokens
    - Add fixture for mock database session
    - Add fixture for mock JWKS endpoint
  - [x] 14.7 Run tests and verify coverage
    - Run pytest on all test files
    - Verify critical workflows pass (authentication, health checks, tenant context)
    - Expected total tests: approximately 20-26 tests
    - Fix any failing tests
    - Do NOT aim for comprehensive coverage - focus on critical paths only

**Deliverables:**
- `backend/tests/conftest.py` (test fixtures)
- `backend/tests/test_auth/test_jwt_validator.py` (JWT validation tests)
- `backend/tests/test_api/test_auth.py` (authentication endpoint tests)
- `backend/tests/test_api/test_health.py` (health check tests)
- `backend/tests/test_middleware/test_tenant_context.py` (tenant context tests)
- `backend/tests/test_middleware/test_logging.py` (logging tests)
- `backend/tests/test_middleware/test_exception.py` (exception handling tests)

**Acceptance Criteria:**
- Approximately 20-26 tests written covering critical workflows
- All tests pass successfully
- Tests cover JWT validation, authentication endpoints, health checks, middleware
- Test fixtures provide reusable mocks for JWT, database, JWKS
- Tests focus on critical paths, not exhaustive edge cases
- Tests do NOT require running full application stack

**Effort:** L (8-10 hours)

---

## Summary & Execution Notes

### Phase Dependencies
```
Phase 1 (Project Setup)
    ↓
Phase 2 (Database) + Phase 3 (Configuration)
    ↓
Phase 4 (Authentication Core)
    ↓
Phase 5 (Middleware)
    ↓
Phase 6 (API Endpoints) + Phase 7 (Error Handling/CORS)
    ↓
Phase 8 (Deployment)
    ↓
Phase 9 (Documentation) + Phase 10 (Testing)
```

### Parallel Work Opportunities
- **Phase 2 & 3** can be worked on in parallel (Database + Configuration)
- **Phase 6 & 7** can partially overlap (API Endpoints + Error Handling)
- **Phase 9** documentation can start early and continue throughout
- **Phase 10** testing can start as soon as phases 4-7 are complete

### Critical Path Highlights
1. **Project Setup (Phase 1)** - Blocks everything
2. **Database + Configuration (Phases 2-3)** - Enables authentication
3. **Authentication Core (Phase 4)** - Critical for API functionality
4. **Middleware (Phase 5)** - Required for tenant isolation
5. **Deployment (Phase 8)** - Enables Railway deployment
6. **Testing (Phase 10)** - Validates critical workflows

### Implementer Assignment Summary
- **api-engineer**: 11 task groups (Phases 1, 3-9 excluding database work)
- **database-engineer**: 1 task group (Phase 2)
- **testing-engineer**: 1 task group (Phase 10)

### Estimated Effort Breakdown
- **XS (0-2 hours):** 0 tasks
- **S (2-4 hours):** 3 task groups (12-16 hours)
- **M (4-7 hours):** 6 task groups (30-42 hours)
- **L (7-10 hours):** 5 task groups (35-50 hours)
- **XL (10+ hours):** 0 tasks

**Total Estimated Effort:** 77-108 hours (approximately 10-14 working days for one person, 6-10 days with parallel work)

### Success Criteria Checklist
- [ ] Railway template deploys successfully with one-click
- [ ] Health check endpoints return 200 OK within 1 minute of deployment
- [ ] JWT tokens validate successfully with JWKS endpoint
- [ ] Tenant ID extracted from JWT claims
- [ ] All logs output structured JSON to stdout
- [ ] Database connection pool handles 20 concurrent requests
- [x] All 5 documentation files complete and accurate
- [x] Approximately 20-26 strategic tests pass
- [ ] Local development setup works in < 1 hour following README

### Out of Scope Reminders
- User CRUD operations
- Password reset flows
- MFA configuration UI
- Session/refresh token logic
- Rate limiting middleware
- Document ingestion endpoints
- RAG/search endpoints
- Actual audit log implementation
- RBAC implementation
- AWS infrastructure provisioning (Feature 3)

### Next Steps After Completion
This feature establishes the foundation for:
- **Feature 2:** User & Tenant Management (data models)
- **Feature 3:** AWS Infrastructure Provisioning (VPC, RDS, S3, KMS)
- **Feature 4:** Encryption Key Management (per-tenant KMS keys)
- **Feature 5:** Document Ingestion API (S3 upload, metadata storage)
- **Feature 10:** Audit Logging (immutable audit trail)
- **Feature 13:** Authorization & RBAC (permission system)

All future features will build on the patterns established in this foundational scaffold.
