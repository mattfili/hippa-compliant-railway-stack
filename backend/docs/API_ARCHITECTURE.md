# API Architecture & Extension Points

This document explains the architecture patterns, project structure, and extension points for adding new features to the HIPAA-compliant backend API.

## Table of Contents

- [Project Structure](#project-structure)
- [Component Responsibilities](#component-responsibilities)
- [Domain-Based Route Organization](#domain-based-route-organization)
- [Adding New API Domains](#adding-new-api-domains)
- [Middleware Execution Order](#middleware-execution-order)
- [Adding Custom Middleware](#adding-custom-middleware)
- [Database Connection Patterns](#database-connection-patterns)
- [Error Handling Conventions](#error-handling-conventions)
- [Logging Patterns](#logging-patterns)
- [Future Extension Points](#future-extension-points)

## Project Structure

```
backend/app/
├── main.py                      # FastAPI application factory and CORS setup
├── config.py                    # Pydantic settings (environment + AWS Secrets)
│
├── api/v1/                      # API routes organized by domain
│   ├── auth.py                  # Authentication endpoints (login, logout, validate)
│   ├── health.py                # Health check endpoints (liveness, readiness)
│   └── documents.py             # Future: Document management endpoints
│
├── auth/                        # Authentication layer
│   ├── jwt_validator.py         # JWT signature and claim validation
│   ├── tenant_extractor.py      # Extract tenant_id from JWT claims
│   └── dependencies.py          # FastAPI dependencies for auth
│
├── middleware/                  # Request/response middleware
│   ├── tenant_context.py        # Tenant isolation and context injection
│   ├── logging.py               # Structured request logging
│   └── exception.py             # Standardized error handling
│
├── database/                    # Database layer
│   ├── engine.py                # SQLAlchemy async engine with pooling
│   └── base.py                  # Declarative base with common fields
│
├── models/                      # SQLAlchemy database models
│   ├── tenant.py                # Future: Tenant model
│   ├── user.py                  # Future: User model
│   └── document.py              # Future: Document model
│
└── utils/                       # Shared utilities
    ├── logger.py                # JSON logging configuration
    ├── errors.py                # Error registry and custom exceptions
    └── secrets_manager.py       # AWS Secrets Manager client
```

## Component Responsibilities

### Application Layer (`main.py`)

**Purpose**: FastAPI application factory and global configuration

**Responsibilities**:
- Create FastAPI application instance with metadata
- Register middleware in correct execution order
- Configure CORS with environment-based origins
- Register API routers with versioned prefixes
- Define root health check endpoint

**Pattern**:
```python
def create_app() -> FastAPI:
    app = FastAPI(title=..., version=...)

    # Register middleware (order matters!)
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(CORSMiddleware, ...)

    # Register routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")

    return app
```

### API Routers (`api/v1/*.py`)

**Purpose**: Define HTTP endpoints grouped by business domain

**Responsibilities**:
- Define routes with appropriate HTTP methods (GET, POST, PUT, DELETE)
- Parse and validate request data using Pydantic models
- Call business logic and return responses
- Apply authentication/authorization dependencies
- Access tenant context from request state

**Pattern**:
```python
from fastapi import APIRouter, Depends, Request
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/domain", tags=["Domain"])

@router.get("/")
async def list_items(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    tenant_id = request.state.tenant_id
    # Query items for this tenant
    return {"items": []}
```

### Authentication Layer (`auth/*.py`)

**Purpose**: JWT validation, token parsing, and user context extraction

**Responsibilities**:
- Fetch and cache JWKS keys from IdP
- Validate JWT signature and standard claims
- Extract tenant_id from custom claims
- Provide FastAPI dependencies for protected routes
- Handle authentication errors with appropriate HTTP status codes

**Key Components**:
- **JWTValidator**: Validates JWT signatures using JWKS endpoint
- **TenantExtractor**: Parses tenant_id from JWT claims
- **get_current_user**: FastAPI dependency for authentication

### Middleware Layer (`middleware/*.py`)

**Purpose**: Cross-cutting concerns applied to all requests

**Responsibilities**:
- **Exception Middleware**: Catch and format all errors
- **Tenant Context Middleware**: Extract and validate tenant isolation
- **Logging Middleware**: Add request_id and context to logs

**Execution Order** (from first to last):
1. Exception handling (catches all errors)
2. CORS (handles preflight requests)
3. Logging (adds request_id)
4. Tenant context (after authentication)
5. Route handler

### Database Layer (`database/*.py`)

**Purpose**: Async database connection and session management

**Responsibilities**:
- Create async SQLAlchemy engine with connection pooling
- Provide session factory for database operations
- Implement retry logic for transient connection failures
- Define base model with common fields (id, created_at, updated_at)

**Pattern**:
```python
from app.database.engine import get_session
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/items")
async def get_items(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Item))
    return result.scalars().all()
```

### Models (`models/*.py`)

**Purpose**: SQLAlchemy ORM models representing database tables

**Responsibilities**:
- Define table schema using SQLAlchemy declarative syntax
- Inherit from Base for common fields
- Define relationships between tables
- Include tenant_id column for tenant isolation

**Pattern**:
```python
from app.database.base import Base
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Document(Base):
    __tablename__ = "documents"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship(back_populates="documents")
```

### Utilities (`utils/*.py`)

**Purpose**: Shared helper functions and configurations

**Responsibilities**:
- **logger.py**: Configure structured JSON logging
- **errors.py**: Define error codes and custom exceptions
- **secrets_manager.py**: Fetch secrets from AWS Secrets Manager

## Domain-Based Route Organization

### URL Structure Pattern

All API endpoints follow this structure:

```
/api/{version}/{domain}/{resource}[/{id}][/{action}]
```

**Examples**:
- `/api/v1/auth/callback` - Authentication callback
- `/api/v1/auth/validate` - Validate JWT token
- `/api/v1/health/live` - Liveness probe
- `/api/v1/health/ready` - Readiness probe
- `/api/v1/documents` - List documents (future)
- `/api/v1/documents/abc-123` - Get specific document (future)
- `/api/v1/documents/abc-123/download` - Download document (future)

### Versioning Strategy

**Current Version**: v1

API versioning uses URL path prefixing (`/api/v1/*`) to enable:
- Breaking changes without disrupting existing clients
- Gradual migration from old to new versions
- Side-by-side version support during transition

**When to Increment Version**:
- Breaking changes to request/response formats
- Removal of endpoints or fields
- Changes to authentication requirements
- Major architectural changes

**Minor Changes (No Version Bump)**:
- Adding new optional fields to responses
- Adding new endpoints
- Adding query parameters
- Bug fixes and performance improvements

## Adding New API Domains

Follow this step-by-step process to add a new business domain to the API.

### Example: Adding Documents Domain

#### Step 1: Create Router File

Create `backend/app/api/v1/documents.py`:

```python
"""
Document management endpoints.

Provides APIs for uploading, listing, and downloading documents
with automatic tenant isolation.
"""

from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.dependencies import get_current_user
from app.database.engine import get_session
from app.models.document import Document
from app.utils.errors import ErrorRegistry, DocumentNotFoundError

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/")
async def list_documents(
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    List all documents for the current tenant.

    Returns:
        List of document metadata for tenant-scoped documents
    """
    tenant_id = request.state.tenant_id
    user_id = current_user["user_id"]

    # Query documents filtered by tenant_id
    result = await db.execute(
        select(Document)
        .where(Document.tenant_id == tenant_id)
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    return {
        "documents": [doc.to_dict() for doc in documents],
        "tenant_id": tenant_id,
    }


@router.post("/")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a new document.

    The document will be associated with the current tenant and user.
    """
    tenant_id = request.state.tenant_id
    user_id = current_user["user_id"]

    # Create document record
    document = Document(
        tenant_id=tenant_id,
        user_id=user_id,
        filename=file.filename,
        content_type=file.content_type,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return {
        "document": document.to_dict(),
        "message": "Document uploaded successfully",
    }


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Get document metadata by ID.

    Only returns document if it belongs to the current tenant.
    """
    tenant_id = request.state.tenant_id

    # Query document with tenant isolation
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
        .where(Document.tenant_id == tenant_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise DocumentNotFoundError(f"Document {document_id} not found")

    return {"document": document.to_dict()}
```

#### Step 2: Register Router in Main App

Update `backend/app/main.py`:

```python
from app.api.v1 import auth, health, documents  # Add documents import

def create_app() -> FastAPI:
    app = FastAPI(...)

    # ... middleware setup ...

    # Register routers
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")  # Add this line

    return app
```

#### Step 3: Create Database Model (if needed)

Create `backend/app/models/document.py`:

```python
from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Document(Base):
    __tablename__ = "documents"

    # Tenant isolation (required on all models)
    tenant_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True,
        comment="Tenant identifier for data isolation"
    )

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False,
        comment="User who uploaded the document"
    )

    # Document metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="documents")
```

#### Step 4: Create Database Migration

```bash
# Generate migration
alembic revision -m "add_documents_table"
```

Edit the generated migration file:

```python
def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('content_type', sa.String(100)),
        sa.Column('file_size', sa.Integer()),
        sa.Column('s3_key', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create indexes for performance
    op.create_index('idx_documents_tenant_created', 'documents', ['tenant_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('idx_documents_tenant_created')
    op.drop_table('documents')
```

#### Step 5: Add Custom Error Codes

Update `backend/app/utils/errors.py`:

```python
class ErrorRegistry:
    # ... existing error codes ...

    # Document errors
    DOC_001 = "Document not found"
    DOC_002 = "Invalid document format"
    DOC_003 = "Document size exceeds limit"
    DOC_004 = "Document upload failed"


class DocumentNotFoundError(APIException):
    def __init__(self, message: str = "Document not found"):
        super().__init__(
            error_code="DOC_001",
            message=message,
            status_code=404
        )
```

#### Step 6: Document Error Codes

Add to `backend/docs/ERROR_CODES.md`:

```markdown
### Document Errors (DOC_001 - DOC_999)

#### DOC_001: Document not found
- **Description**: Requested document does not exist or user lacks access
- **HTTP Status**: 404 Not Found
- **Common Causes**: Invalid document ID, document deleted, cross-tenant access attempt
- **Resolution**: Verify document ID, check user has access to tenant

#### DOC_002: Invalid document format
- **Description**: Uploaded file format not supported
- **HTTP Status**: 400 Bad Request
- **Common Causes**: Unsupported file extension, corrupted file
- **Resolution**: Check supported formats in documentation
```

#### Step 7: Add Tests

Create `backend/tests/test_api/test_documents.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, auth_token: str):
    response = await client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert "documents" in response.json()


@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient, auth_token: str):
    files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
    response = await client.post(
        "/api/v1/documents",
        files=files,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Document uploaded successfully"
```

## Middleware Execution Order

Middleware executes in the order it's registered in `create_app()`.

### Current Middleware Stack

```python
# 1. Exception Handling (first - catches all errors)
app.add_middleware(ExceptionHandlerMiddleware)

# 2. CORS (handles preflight OPTIONS requests)
app.add_middleware(CORSMiddleware, ...)

# 3. Request Logging (adds request_id to context)
app.add_middleware(LoggingMiddleware)

# 4. Tenant Context (after authentication dependency)
app.add_middleware(TenantContextMiddleware)

# Route Handler
# Middleware executes in reverse order on response
```

### Request Flow

```
Request
  ↓
Exception Middleware (try)
  ↓
CORS Middleware (preflight check)
  ↓
Logging Middleware (generate request_id)
  ↓
Tenant Context Middleware (extract tenant_id)
  ↓
Authentication Dependency (validate JWT)
  ↓
Route Handler (business logic)
  ↓
Tenant Context Middleware (cleanup)
  ↓
Logging Middleware (log response)
  ↓
CORS Middleware (add headers)
  ↓
Exception Middleware (catch/format errors)
  ↓
Response
```

## Adding Custom Middleware

### Basic Middleware Pattern

```python
# backend/app/middleware/custom.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Pre-request processing
        request.state.custom_value = "something"

        # Call next middleware/route handler
        response = await call_next(request)

        # Post-request processing
        response.headers["X-Custom-Header"] = "value"

        return response
```

### Register in Application

```python
# backend/app/main.py
from app.middleware.custom import CustomMiddleware

def create_app() -> FastAPI:
    app = FastAPI(...)

    # Add custom middleware
    app.add_middleware(CustomMiddleware)

    return app
```

### Middleware Best Practices

1. **Order Matters**: Exception handling should be first to catch all errors
2. **Context Injection**: Use `request.state` to pass data between middleware
3. **Performance**: Keep middleware lightweight, avoid blocking operations
4. **Error Handling**: Let exception middleware catch errors, don't swallow them
5. **HIPAA Compliance**: Never log sensitive data (tokens, PHI) in middleware

## Database Connection Patterns

### Using Async Sessions

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.engine import get_session
from fastapi import Depends


@router.get("/items")
async def get_items(db: AsyncSession = Depends(get_session)):
    # Simple query
    result = await db.execute(select(Item))
    items = result.scalars().all()
    return {"items": items}
```

### Tenant-Scoped Queries

**Always** filter by tenant_id to ensure tenant isolation:

```python
@router.get("/items")
async def get_items(
    request: Request,
    db: AsyncSession = Depends(get_session)
):
    tenant_id = request.state.tenant_id

    # Query with tenant filter
    result = await db.execute(
        select(Item)
        .where(Item.tenant_id == tenant_id)
        .order_by(Item.created_at.desc())
    )
    return {"items": result.scalars().all()}
```

### Transaction Management

```python
@router.post("/items")
async def create_item(
    item_data: dict,
    db: AsyncSession = Depends(get_session)
):
    try:
        # Create item
        item = Item(**item_data)
        db.add(item)

        # Commit transaction
        await db.commit()
        await db.refresh(item)

        return {"item": item.to_dict()}
    except Exception as e:
        # Rollback on error (automatic with get_session dependency)
        await db.rollback()
        raise
```

### Connection Pooling

The database engine is configured with connection pooling in `database/engine.py`:

```python
engine = create_async_engine(
    database_url,
    pool_size=10,          # Connections to keep in pool
    max_overflow=10,       # Additional connections when pool full
    pool_timeout=30,       # Seconds to wait for connection
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600,     # Recycle connections after 1 hour
)
```

## Error Handling Conventions

### Error Code Registry

All errors are registered in `app/utils/errors.py`:

```python
class ErrorRegistry:
    # Authentication errors
    AUTH_001 = "Invalid token"
    AUTH_002 = "CSRF validation failed"
    AUTH_003 = "Token expired"

    # System errors
    SYS_001 = "Database unreachable"
    SYS_002 = "Secrets Manager unavailable"

    # Custom domain errors
    DOC_001 = "Document not found"
```

### Custom Exceptions

```python
class APIException(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        detail: str = "",
        status_code: int = 500
    ):
        self.error_code = error_code
        self.message = message
        self.detail = detail
        self.status_code = status_code


class DocumentNotFoundError(APIException):
    def __init__(self, message: str = "Document not found"):
        super().__init__(
            error_code="DOC_001",
            message=message,
            status_code=404
        )
```

### Raising Errors in Routes

```python
from app.utils.errors import DocumentNotFoundError

@router.get("/{doc_id}")
async def get_document(doc_id: str):
    if not document:
        raise DocumentNotFoundError(f"Document {doc_id} not found")
```

### Error Response Format

All errors return this standardized format:

```json
{
  "error": {
    "code": "DOC_001",
    "message": "Document not found",
    "detail": "Document abc-123 not found",
    "request_id": "req-789-def-012"
  }
}
```

## Logging Patterns

### Structured JSON Logging

All logs output in JSON format for CloudWatch parsing:

```json
{
  "timestamp": "2025-10-15T12:34:56.789Z",
  "level": "INFO",
  "logger": "app.api.v1.documents",
  "message": "Document uploaded",
  "request_id": "req-123-abc-456",
  "user_id": "usr-789",
  "tenant_id": "org-456",
  "context": {
    "document_id": "doc-123",
    "filename": "report.pdf",
    "file_size": 1024000
  }
}
```

### Logging in Route Handlers

```python
import logging

logger = logging.getLogger(__name__)


@router.post("/documents")
async def upload_document(
    request: Request,
    file: UploadFile = File(...)
):
    tenant_id = request.state.tenant_id
    request_id = request.state.request_id

    logger.info(
        "Document upload started",
        extra={
            "request_id": request_id,
            "tenant_id": tenant_id,
            "filename": file.filename,
            "content_type": file.content_type,
        }
    )

    # ... upload logic ...

    logger.info(
        "Document upload completed",
        extra={
            "request_id": request_id,
            "tenant_id": tenant_id,
            "document_id": document.id,
        }
    )
```

### HIPAA Logging Compliance

**What to Log**:
- Request metadata (method, path, status_code, duration)
- User context (user_id, tenant_id, request_id)
- Business events (document uploaded, query executed)
- Error conditions (with sanitized messages)

**What NOT to Log**:
- Authorization tokens or headers
- PHI data (patient names, SSNs, medical records)
- Query parameters containing sensitive data
- Full exception stack traces to external systems
- Database passwords or API keys

**Log Sanitization Example**:

```python
# BAD - Logs sensitive data
logger.info(f"User {user_email} accessed patient {patient_name}")

# GOOD - Logs only reference IDs
logger.info(
    "User accessed patient record",
    extra={
        "user_id": user_id,
        "tenant_id": tenant_id,
        "patient_id": patient_id,  # Reference ID only
    }
)
```

## Future Extension Points

### Documented but Not Implemented

These patterns are documented for future implementation:

#### 1. Document Ingestion API (Feature 5)

Future endpoints:
- `POST /api/v1/documents` - Upload document
- `GET /api/v1/documents/{id}/download` - Download document
- `DELETE /api/v1/documents/{id}` - Delete document

Integration points:
- S3 upload with multipart support
- Metadata extraction
- Virus scanning
- Document chunking for embeddings

#### 2. RAG Query API (Features 8-9)

Future endpoints:
- `POST /api/v1/query` - Semantic search query
- `GET /api/v1/query/{id}` - Retrieve query result
- `POST /api/v1/embeddings` - Generate embeddings

Integration points:
- Vector similarity search with pgvector
- AWS Bedrock for embeddings and LLM
- Query result caching
- Context window management

#### 3. Audit Logging (Feature 10)

Future implementation:
- Immutable audit table with append-only writes
- Audit event types documented in HIPAA_READINESS.md
- Automated audit log export for compliance reviews
- Query audit logs by user, tenant, or time range

#### 4. Authorization & RBAC (Feature 13)

Future implementation:
- Permission checks on endpoints
- Role assignment (admin, user, read-only)
- Tenant-level permissions
- Resource-level permissions

### Extension Guidelines

When adding new features:

1. **Follow Domain Pattern**: Group related endpoints in one router
2. **Tenant Isolation**: Always filter by tenant_id
3. **Error Codes**: Add to ErrorRegistry and document in ERROR_CODES.md
4. **Logging**: Log business events with context, never log PHI
5. **Tests**: Write tests for critical workflows
6. **Documentation**: Update this file with new patterns

### Architecture Review Checklist

Before merging new API domains, verify:

- [ ] Router registered in `main.py`
- [ ] Authentication dependency applied to protected routes
- [ ] Tenant context accessed from `request.state.tenant_id`
- [ ] All queries filtered by tenant_id
- [ ] Error codes added to ErrorRegistry
- [ ] Custom exceptions inherit from APIException
- [ ] Structured logging with context
- [ ] No PHI in logs
- [ ] Tests cover happy path and error cases
- [ ] Documentation updated (README, API_ARCHITECTURE, ERROR_CODES)

## Conclusion

This architecture provides a solid foundation for HIPAA-compliant healthcare applications with:

- **Clear separation of concerns** between layers
- **Tenant isolation** enforced at the middleware level
- **Extensible patterns** for adding new business domains
- **Standardized error handling** with error code registry
- **HIPAA-compliant logging** with no PHI exposure

For specific implementation details, see:
- [ERROR_CODES.md](ERROR_CODES.md) - Complete error code registry
- [AUTH_CONFIGURATION.md](AUTH_CONFIGURATION.md) - Authentication setup
- [DEPLOYMENT.md](DEPLOYMENT.md) - Railway and AWS deployment
- [HIPAA_READINESS.md](HIPAA_READINESS.md) - Compliance checklist
