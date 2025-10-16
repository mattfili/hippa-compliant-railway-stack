"""
Database models for the application.

All models use:
- UUID primary keys (String(36))
- Timezone-aware timestamps (TIMESTAMPTZ)
- Soft deletes where applicable (Tenant, User, Document)
- Tenant isolation via RLS and foreign keys

Models:
    Tenant: Organization/customer model for multi-tenant isolation
    User: User account model with tenant association
    Document: Document metadata with S3 references and vector embeddings
    AuditLog: Immutable append-only audit log model
"""

from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.tenant import Tenant
from app.models.user import User

__all__ = [
    "AuditLog",
    "Document",
    "Tenant",
    "User",
]
