# Product Roadmap

## Overview

This roadmap outlines the development path from initial infrastructure setup to a production-ready HIPAA-compliant template. Features are ordered to build foundational capabilities first, then layer on compliance, intelligence, and developer experience features.

## Ordered Feature Checklist

1. [x] **Backend API Scaffold with Authentication** — FastAPI application with route structure, OIDC/SAML authentication integration with MFA support, JWT token handling, and basic health check endpoints. Includes tenant context middleware that extracts and validates tenant ID from authenticated requests. `M`

2. [x] **Database Schema and Multi-Tenant Data Model** — PostgreSQL schema with tenant isolation patterns, pgvector extension setup, core tables (tenants, users, documents, audit_logs), foreign key relationships, and database migrations framework. Includes indexes optimized for tenant-scoped queries. Includes Railway configuration for automated provisioning. `M`

3. [ ] **AWS Infrastructure Provisioning** — Terraform templates to create VPC with public/private subnets, RDS PostgreSQL instance with encryption at rest, S3 buckets with versioning and encryption, KMS master keys, security groups, and IAM roles. Includes Railway configuration for automated provisioning. `L`

4. [ ] **Per-Tenant Encryption Key Management** — KMS key generation workflow that creates unique encryption keys for each tenant, key metadata storage, tenant-key association logic, and encryption/decryption utilities that automatically select correct key based on tenant context. Includes key rotation capability. `L`

5. [ ] **Document Ingestion and Storage Pipeline** — API endpoints for document upload, validation (file type, size limits), metadata extraction, S3 storage with tenant-specific prefixes, server-side encryption using tenant KMS keys, and database record creation linking S3 objects to tenant/user. `M`

6. [ ] **PDF Processing and Text Extraction** — Document processing service that downloads PDFs from S3, extracts text content using PDF parsing libraries, handles multi-page documents, chunks text into optimal segments (500-1000 tokens) for embedding, and stores processed chunks with document references. `S`

7. [ ] **Embedding Generation with Amazon Bedrock** — Integration with Titan Embeddings on Bedrock to generate vector representations of document chunks, batch processing for efficiency, error handling for API rate limits, storage of embeddings in pgvector columns, and embedding versioning for model updates. `M`

8. [ ] **Vector Similarity Search with pgvector** — Query API that accepts natural language questions, generates query embeddings via Bedrock, performs cosine similarity search using pgvector indexes, retrieves top-K relevant document chunks with metadata, and filters results by tenant context for isolation. `S`

9. [ ] **RAG Response Generation with Claude** — Integration with Claude on Amazon Bedrock that takes user query and retrieved document chunks as context, generates responses with citations to source documents, implements streaming for real-time response delivery, and includes retry logic for reliability. `M`

10. [ ] **Comprehensive Audit Logging System** — Append-only audit log table capturing all CRUD operations, authentication events, document access, and administrative actions with user ID, tenant ID, timestamp, IP address, action type, and affected resource IDs. Includes automated triggers on sensitive tables. `M`

11. [ ] **Self-Hosted Retool Deployment in VPC** — Docker-based Retool deployment within private subnet, PostgreSQL database for Retool metadata, reverse proxy configuration for secure access, connection to application database as data source, and environment configuration for production readiness. `L`

12. [ ] **Pre-Built Retool Dashboards and Components** — Sample Retool applications including audit log viewer with filtering/export, document library with upload/search, tenant management interface, user administration, and customizable form templates. Includes documentation for extending dashboards. `M`

13. [ ] **Role-Based Access Control Implementation** — Database schema for roles and permissions, middleware for checking permissions on API requests, predefined role templates (admin, clinician, analyst, patient), tenant-admin role for delegated administration, and UI for role assignment. `M`

14. [ ] **PHI Detection and Scrubbing Utilities** — Service for detecting Protected Health Information in text using regex patterns (SSN, MRN, dates) and NLP models, redaction functions for de-identification, integration into document processing pipeline, and optional scrubbing of LLM responses before returning to users. `S`

15. [ ] **Compliance Documentation and HIPAA Readiness Guide** — Comprehensive documentation including README.md with setup instructions, SECURITY.md with threat model and controls, HIPAA_READINESS.md checklist for audits, DATA_FLOWS.md with architecture diagrams, and AUDIT_DASHBOARD.md for compliance reporting. `S`

16. [ ] **Anomaly Detection for Audit Logs** — Background job that analyzes audit logs for suspicious patterns (unusual access times, bulk data exports, cross-tenant query attempts, repeated failed authentications), configurable alerting rules, and dashboard for security team to review flagged events. `M`

17. [ ] **Automated Testing Suite** — Unit tests for core services (encryption, document processing, RAG pipeline), integration tests for API endpoints with test tenant data, security tests for authentication and authorization, performance tests for vector search latency, and CI pipeline configuration. `L`

18. [ ] **Railway Template Configuration and Publishing** — railway.json with service definitions, environment variable templates with secure defaults, startup scripts for database initialization and migrations, health check configuration, resource allocation settings, and template documentation for one-click deployment. `M`

## Effort Scale

- **XS**: 1 day - Small, isolated changes
- **S**: 2-3 days - Single feature or service
- **M**: 1 week - Moderate complexity with integration
- **L**: 2 weeks - Complex feature requiring multiple services
- **XL**: 3+ weeks - Major architectural component

## Development Notes

### Dependencies and Sequencing

- **Features 1-3** form the foundation and should be completed first (authentication, data model, infrastructure)
- **Feature 4** (tenant encryption) must be completed before Feature 5 (document storage) to ensure data is encrypted from first upload
- **Features 5-7** (ingestion, processing, embedding) form the document pipeline and should be completed sequentially
- **Feature 8-9** (search, RAG) depend on the document pipeline and can begin once embeddings are available
- **Feature 11-12** (Retool) can be developed in parallel with Features 8-10 once database schema is stable
- **Feature 17** (testing) should be developed incrementally alongside features, not saved for the end

### Prioritization Strategy

The roadmap prioritizes establishing a secure, compliant foundation first (Features 1-4), then building the core value proposition of document intelligence (Features 5-9), followed by compliance features (Features 10, 14, 16), developer experience (Features 11-12, 15, 18), and access control (Feature 13). This ensures the template can demonstrate RAG capabilities early while maintaining security throughout.

### Phase Groupings

While features should be completed in order, they can be conceptually grouped into phases:

- **Phase 1 (Foundation)**: Features 1-4 - Core infrastructure and security
- **Phase 2 (Data Pipeline)**: Features 5-7 - Document ingestion and processing
- **Phase 3 (Intelligence)**: Features 8-9 - RAG and semantic search
- **Phase 4 (Compliance)**: Features 10, 14, 16 - Audit and security monitoring
- **Phase 5 (Developer Experience)**: Features 11-12, 15, 18 - UI, docs, deployment
- **Phase 6 (Access Control & Testing)**: Features 13, 17 - RBAC and quality assurance

### MVP Definition

A minimum viable product includes Features 1-10, which provides:
- Secure multi-tenant foundation
- Complete RAG pipeline for document intelligence
- Basic audit logging for compliance
- API-driven architecture (Retool can be added later)

This MVP enables developers to deploy a functioning HIPAA-compliant RAG application and validate value before investing in the full low-code UI layer.
