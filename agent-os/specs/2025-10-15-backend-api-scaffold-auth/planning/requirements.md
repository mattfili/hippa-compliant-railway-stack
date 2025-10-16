# Spec Requirements: Backend API Scaffold with Authentication

## Initial Description

Feature 1: Backend API Scaffold with Authentication

**Description from roadmap.md:**
- Set up FastAPI (Python) or Next.js (TypeScript) project structure
- Configure Railway deployment (railway.json, Dockerfile)
- Implement JWT-based authentication with OIDC/SAML integration
- Create tenant context middleware (extracts tenant_id from auth token)
- Set up environment variable management for AWS credentials, DB connection
- Basic health check and status endpoints
- CORS configuration
- Logging framework setup
- Effort: M (1-2 weeks)

**Context:**
This is the foundation feature for a HIPAA-compliant Railway template with RAG support. The product documentation is in `agent-os/product/` (mission.md, roadmap.md, tech-stack.md).

**Tech Stack (from tech-stack.md):**
- Backend: FastAPI (Python) preferred, or Next.js (TypeScript)
- Auth: JWT with OIDC/SAML, MFA via IdP (Okta/Auth0/Azure AD/Cognito)
- Deployment: Railway with Docker
- Encryption: TLS 1.2+, environment-based secrets

## Requirements Discussion

### First Round Questions and Answers

**Q1: Backend Framework Choice**
**Answer:** FastAPI (Python)

**Q2: Authentication Provider Strategy**
**Answer:** IdP-agnostic using standard OIDC/SAML library (Okta, Auth0, Azure AD, AWS Cognito). Include configuration examples for AWS Cognito.

**Q3: Tenant Context Extraction**
**Answer:** Extract tenant_id from custom JWT claim (tenant_id or organization_id) set by IdP. NO fallback methods.

**Q4: JWT Validation Strategy**
**Answer:** Validate JWTs by fetching IdP's public keys from JWKS endpoint with automatic refresh caching. Configure token expiration requirements (max 60 minutes).

**Q5: Initial API Route Structure**
**Answer:** Organize routes by functional domain (/api/v1/auth/*, /api/v1/health/*, /api/v1/documents/* for future) with tenant context middleware. ONLY implement authentication and health endpoints - NO stubs. Document architecture showing where future stubs would fit.

**Q6: Environment Variables & Secrets Management**
**Answer:** Railway environment variables for deployment config (DATABASE_URL, S3_BUCKET_NAME). AWS Secrets Manager for runtime secrets (KMS keys, IdP client secrets). Provide BOTH .env.example for local dev AND Railway environment variable templates.

**Q7: CORS Configuration**
**Answer:** Allow CORS for specific frontend origins (ALLOWED_ORIGINS env var) with credentials support for cookie-based refresh tokens. Default to permissive localhost for development, require explicit production origins.

**Q8: Logging Framework**
**Answer:** Structured JSON logging (DEBUG, INFO, WARNING, ERROR) with request IDs, tenant IDs, user IDs. Output to stdout for Railway → CloudWatch. Document HIPAA audit events (auth attempts, auth failures) for later implementation in audit logging feature.

**Q9: Error Response Format**
**Answer:** Standardize error format with codes, messages, detail fields: `{"error": {"code": "AUTH_001", "message": "Invalid token", "detail": "Token expired"}}`. Create error code registry from the start.

**Q10: Railway Deployment**
**Answer:** railway.json, Dockerfile, startup scripts for migrations. Configure Railway to automatically run Alembic migrations for base deployment. Future Railway Template users should require manual migration execution.

**Q11: Database Connection & Pooling**
**Answer:** SQLAlchemy async engine with connection pooling (pool size 10-20). Simple automatic reconnection logic for failures. Simple timeout values.

**Q12: Scope Boundaries**
**Answer:** EXCLUDE from this spec: user management CRUD, password reset flows, MFA config UI, session/refresh token logic, rate limiting middleware. Document these as "stretch goals" for later development.

**Overall Goal:** Build a Railway template that users can build on top of. Document "stretch goals" as artifacts showing where features can plug into the opinionated architecture.

### Existing Code to Reference

**Similar Features Identified:**
No similar existing features identified for reference. This is a greenfield project creating the foundational template.

### Follow-up Questions
No follow-up questions were needed. All requirements were clearly specified in the initial answers.

## Visual Assets

### Files Provided:
No visual assets provided.

### Architecture Diagram (Text-Based):
User provided a high-level system architecture diagram showing the overall product architecture:

```
[User / Client UI]
    ↕ (HTTPS, OIDC auth)
[Retool (self-hosted) or Next.js UI] — UI logic, forms, dashboards
    ↕ (calls)
[Backend API Layer (FastAPI / Next.js server)]
    ├── Authentication / Authorization
    ├── Multi-tenant context / key resolution
    ├── Document ingestion APIs
    ├── Query / RAG APIs
    ├── Audit logging component
    └── Key management interface
       ↕
[AWS KMS / Key Store]        ← tenant-specific encryption keys
    ↕
[Storage & Database Layer]
    ├── Encrypted S3 buckets (storing raw files, PDF, blobs)
    ├── RDS + pgvector (storing metadata, embeddings, pointers)
    └── Audit-logs store (append-only table or log infrastructure)
    ↕
[LLM / Embedding Layer (Bedrock)]
    ↕
[Model calls (Claude / Titan embedding) — internal AWS, no egress]
```

**Key Architectural Notes:**
- Document ingestion: optional de-identification/hashing before storing sensitive identifiers
- RAG time: embed query, search embeddings, assemble context, call model
- After model response: mask/scrub before returning or logging (avoid PHI in logs)
- Audit logs capture: who, which tenant, which document IDs, operation, timestamp, success/failure
- Tenant encryption flow: backend fetches tenant's encryption key from KMS for encrypt/decrypt operations

### Visual Insights:
No design mockups or wireframes provided. Architecture diagram shows high-level system design but not UI/UX specifics.

## Requirements Summary

### Functional Requirements

**Core Authentication:**
- IdP-agnostic OIDC/SAML authentication integration supporting Okta, Auth0, Azure AD, AWS Cognito
- JWT token validation using IdP's JWKS endpoint with automatic key refresh and caching
- Token expiration enforcement (maximum 60 minutes)
- Configuration examples specifically for AWS Cognito

**Tenant Context Management:**
- Extract tenant_id from custom JWT claims (tenant_id or organization_id)
- NO fallback tenant resolution methods
- Tenant context middleware to inject tenant context into all requests
- Validate tenant access on every authenticated request

**API Route Structure:**
- Organize routes by functional domain pattern
- Implement /api/v1/auth/* endpoints (login callback, token validation, logout)
- Implement /api/v1/health/* endpoints (liveness, readiness checks)
- Define /api/v1/documents/* route structure in documentation only (no implementation)
- NO stub implementations - only document where future routes would fit

**Configuration Management:**
- Railway environment variables for deployment configuration (DATABASE_URL, S3_BUCKET_NAME, ALLOWED_ORIGINS)
- AWS Secrets Manager integration for runtime secrets (KMS keys, IdP client secrets)
- Provide .env.example for local development
- Provide Railway environment variable templates for deployment

**CORS Configuration:**
- Configurable allowed origins via ALLOWED_ORIGINS environment variable
- Support credentials for cookie-based refresh tokens
- Permissive localhost defaults for development environment
- Require explicit production origin specification

**Logging System:**
- Structured JSON logging with log levels: DEBUG, INFO, WARNING, ERROR
- Include context: request IDs, tenant IDs, user IDs, timestamps
- Output to stdout for Railway → CloudWatch integration
- Document HIPAA audit events for future implementation (auth attempts, auth failures, permission denials)

**Error Handling:**
- Standardized error response format: `{"error": {"code": "AUTH_001", "message": "Invalid token", "detail": "Token expired"}}`
- Create comprehensive error code registry (AUTH_001 through AUTH_999, SYS_001 for system errors, etc.)
- Human-readable messages with technical details
- Consistent error structure across all endpoints

**Database Integration:**
- SQLAlchemy async engine configuration
- Connection pooling with pool size 10-20 connections
- Simple automatic reconnection logic for transient failures
- Simple timeout values for connections
- Alembic for database migrations

**Railway Deployment:**
- railway.json configuration file for Railway platform
- Multi-stage Dockerfile for production builds
- Startup scripts to run Alembic migrations automatically on deployment
- Health check endpoint configuration for Railway
- Documentation for future template users on manual migration execution

### Reusability Opportunities

This is a greenfield project creating the foundational architecture. No existing code to reuse. However, the following patterns should be designed for future extensibility:

**Middleware Patterns:**
- Tenant context middleware should be easily extensible for additional context extraction
- Authentication middleware should support pluggable validation strategies
- Logging middleware should allow custom log enrichment

**Route Organization:**
- Domain-based route structure should set pattern for future features
- Router registration should support modular addition of new route modules
- API versioning strategy should be established from the start

**Configuration Patterns:**
- Environment variable structure should be consistent and predictable
- Secrets management approach should be reusable for all secret types
- Configuration validation should be centralized

**Error Handling Patterns:**
- Error code registry should support easy addition of new error types
- Exception handling decorators should be reusable across routes
- Error logging should be consistent

### Scope Boundaries

**In Scope:**
- FastAPI application scaffolding and project structure
- OIDC/SAML authentication integration (IdP-agnostic)
- JWT token validation with JWKS endpoint integration
- Tenant context extraction from JWT claims
- Tenant context middleware
- Authentication routes (/api/v1/auth/*)
- Health check routes (/api/v1/health/*)
- CORS configuration with environment-based origins
- Structured JSON logging framework
- Standardized error response format and error code registry
- SQLAlchemy async database connection setup
- Alembic database migration framework
- Railway deployment configuration (railway.json, Dockerfile)
- Environment variable management (Railway + AWS Secrets Manager)
- Configuration examples for AWS Cognito
- Documentation of architecture and extension points
- Documentation of HIPAA audit events for future implementation

**Out of Scope (Explicitly Excluded):**
- User management CRUD operations (create, read, update, delete users)
- Password reset flows
- MFA configuration UI
- Session management logic
- Refresh token implementation
- Token refresh endpoints
- Rate limiting middleware
- API key management
- User invitation flows
- Password policies
- Account lockout mechanisms
- Document ingestion endpoints (future Feature 5)
- RAG/search endpoints (future Features 8-9)
- Actual audit log implementation (future Feature 10)
- RBAC implementation (future Feature 13)

**Documented as Stretch Goals (for later features):**
- User management CRUD
- Password reset and forgot password flows
- MFA configuration interfaces
- Session and refresh token management
- Rate limiting and throttling
- Advanced authentication features (API keys, service accounts)

### Technical Considerations

**Technology Stack:**
- Backend Framework: FastAPI (Python 3.11+)
- ORM: SQLAlchemy 2.0 with async support
- Database Migrations: Alembic
- Authentication: python-jose for JWT, httpx for OIDC/JWKS
- Logging: structlog or Python standard logging with JSON formatter
- Validation: Pydantic (built into FastAPI)
- Package Manager: uv (per tech-stack.md)
- Container: Docker with multi-stage builds
- Deployment Platform: Railway

**Integration Points:**
- Identity Providers: Okta, Auth0, Azure AD, AWS Cognito (via OIDC/SAML)
- AWS Secrets Manager: Runtime secret retrieval
- Railway Environment Variables: Deployment configuration
- PostgreSQL Database: Via SQLAlchemy async engine
- CloudWatch Logs: Via stdout JSON logging

**Performance Requirements:**
- Database connection pool: 10-20 connections
- JWT token validation: Cache JWKS keys with TTL refresh
- Health check response: < 100ms
- Authentication request: < 500ms (excluding IdP validation)

**Security Requirements:**
- TLS 1.2+ for all connections
- JWT validation with signature verification
- Token expiration enforcement (max 60 minutes)
- Tenant isolation via middleware
- No PHI in logs (use IDs only)
- CORS restricted to explicit origins in production
- Secrets stored in AWS Secrets Manager (not environment variables)

**HIPAA Compliance Considerations:**
- Unique user identification via IdP
- Access logging (request IDs, user IDs, tenant IDs)
- Audit event documentation for future implementation
- Encryption in transit (TLS 1.2+)
- Tenant isolation architecture
- No PHI in application logs

**Development and Testing:**
- .env.example for local development setup
- Docker Compose for local development environment
- pytest for testing framework (to be set up in future Feature 17)
- Pre-commit hooks for code quality (ruff, black, mypy per tech-stack.md)

**Documentation Requirements:**
- README.md: Setup instructions, local development, deployment guide
- API_ARCHITECTURE.md: Route organization, middleware patterns, extension points
- AUTH_CONFIGURATION.md: IdP setup guides (AWS Cognito examples), JWT claims structure
- DEPLOYMENT.md: Railway deployment, environment variables, secrets management
- ERROR_CODES.md: Error code registry with descriptions
- HIPAA_READINESS.md: Comprehensive HIPAA readiness checklist (documentation only)

### HIPAA Readiness Documentation

The user provided a comprehensive HIPAA readiness checklist to be documented in `docs/HIPAA_READINESS.md`. This is for documentation purposes only and does not require development in this feature. Key areas to document:

**Access Control & Authentication:**
- Unique user IDs via IdP
- Role-Based Access Control (RBAC) - future feature
- Multi-Factor Authentication (MFA) via IdP
- Automatic logoff/session timeout - future feature
- Audit of access logs

**Audit Controls & Logging:**
- Immutable audit logs (append-only table) - future feature
- Log retention (6-10 years)
- Review and alerting on audit logs - future feature
- Capture: who, what, when, where, outcome

**Encryption & Key Management:**
- Encryption at rest (RDS, S3 with KMS)
- Encryption in transit (TLS 1.2+)
- AWS KMS for key management
- Tenant-based encryption keys (per-tenant KMS keys)

**Data Integrity, Backup & Recovery:**
- RDS automated backups (30-day retention)
- S3 versioning enabled
- Disaster recovery procedures
- Data integrity validation

**Transmission Security:**
- TLS 1.2+ for all communications
- VPC network segmentation
- Security groups and NACLs

**De-identification & Data Minimization:**
- Optional de-identification before storage (future feature)
- PHI scrubbing utilities (future Feature 14)
- Minimize PHI in logs

**VPC & Network Segmentation:**
- Private subnets for database
- Public subnets for API with restricted security groups
- NAT Gateway for outbound internet access

**Business Associate Agreements (BAA):**
- AWS BAA coverage (RDS, S3, KMS, Bedrock)
- Railway BAA coverage

**Policies & Procedures:**
- Security policies documentation
- Incident response procedures
- Data breach notification procedures

**Training & Oversight:**
- Security awareness training requirements
- Periodic security reviews

**Periodic Audits & Penetration Testing:**
- Regular security audits
- Penetration testing recommendations
- Vulnerability scanning

## Additional Context

### Product Mission Alignment
This feature serves as the foundation (Phase 1) of the HIPAA-Compliant Low-Code App Template with RAG Support. It directly enables:
- Primary user need: Deploy compliant infrastructure without 6-12 months of specialized work
- Compliance-first architecture differentiator
- Foundation for multi-tenant isolation
- Basis for future RAG pipeline integration

### Roadmap Position
This is Feature 1 in the product roadmap and must be completed before any other features. It establishes:
- Authentication and authorization patterns
- Multi-tenant architecture foundation
- Deployment and configuration patterns
- Logging and error handling standards

All subsequent features (Feature 2-18) depend on the patterns established here.

### Success Metrics
This feature contributes to:
- Time to First Compliant Deployment: < 1 hour (this feature enables rapid deployment)
- HIPAA Audit Success Rate: 95%+ (compliance-first foundation)
- Developer Net Promoter Score: NPS > 50 (developer experience focus)
- Setup Friction Score: < 3 issues requiring support (clear documentation)

### Key Design Principles
1. **Compliance by Default:** Every design decision prioritizes HIPAA compliance
2. **Developer Experience:** Simple setup, clear documentation, sensible defaults
3. **Extensibility:** Architecture supports future features without refactoring
4. **Tenant Isolation:** Multi-tenancy is architectural, not bolted on
5. **Railway Template Ready:** Designed for one-click deployment as Railway template
