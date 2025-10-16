# Tech Stack

## Overview

This document outlines all technology choices for the HIPAA-Compliant Low-Code App Template with RAG Support. All selections prioritize HIPAA compliance, leveraging only services covered by Business Associate Agreements (BAA) and implementing required security controls.

## Framework & Runtime

### Application Framework
- **Backend API**: FastAPI (Python) 
  - **FastAPI Rationale**: High performance async framework with automatic OpenAPI documentation, native Pydantic validation for request/response schemas, excellent for ML/AI integration with Python ecosystem

### Language & Runtime
- **Backend**: Python 3.11+ or Node.js 20+ LTS
  - **Python**: For FastAPI backend, provides rich ecosystem for document processing (PyPDF2, pdfplumber), ML libraries, and AWS SDK (boto3)


### Package Managers
- **Python**: `uv` 
- **Node.js**: `npm` 

## Frontend

### JavaScript Framework
- **Primary**: Self-hosted Retool (low-code platform)
  - **Rationale**: Enables non-technical users to customize dashboards and forms, drastically reduces development time for internal tools, can be self-hosted within VPC for HIPAA compliance
- **Secondary/Optional**: Next.js with React
  - **Rationale**: For custom patient-facing UIs or when low-code limitations are reached, provides full design flexibility

### CSS Framework
- **Tailwind CSS**
  - **Rationale**: Utility-first CSS framework enables rapid UI development, excellent for prototyping, small bundle sizes with purging, integrates well with React components

### UI Components
- **shadcn/ui** (for Next.js frontend)
  - **Rationale**: Accessible, customizable component library built on Radix UI primitives, copy-paste components provide full control without dependency bloat, consistent with modern React patterns
- **Retool Built-in Components** (for Retool dashboards)
  - **Rationale**: Pre-built tables, forms, charts, and controls optimized for data-driven applications

## Database & Storage

### Primary Database
- **PostgreSQL 15+ on AWS RDS**
  - **Rationale**: HIPAA-eligible when configured correctly, supports pgvector extension for vector similarity search, robust transaction support for audit logs, proven reliability at scale, encryption at rest via KMS, automated backups
  - **Configuration**: Multi-AZ for high availability, automated backups with 30-day retention, encryption at rest enabled, TLS 1.2+ enforced for connections

### Vector Database Extension
- **pgvector**
  - **Rationale**: Native PostgreSQL extension eliminates need for separate vector database, reduces infrastructure complexity, supports cosine similarity and L2 distance for semantic search, scales to millions of vector

### Object Storage
- **AWS S3**
  - **Rationale**: HIPAA-eligible under BAA, server-side encryption with KMS (SSE-KMS), versioning for audit trail, lifecycle policies for cost optimization, scales to petabytes
  - **Configuration**: Default encryption enabled with KMS, versioning enabled, bucket policies restricting access to application IAM roles only, access logging enabled

### ORM/Query Builder
- **SQLAlchemy 2.0** (for Python/FastAPI)
  - **Rationale**: Mature ORM with async support, flexible for both ORM and raw SQL, excellent for complex queries, strong type hinting with SQLAlchemy 2.0

## AI & Machine Learning

### Large Language Model
- **Amazon Bedrock - Claude 3.5 Sonnet or Claude 3 Haiku**
  - **Rationale**: HIPAA-eligible under AWS BAA, no data retention by Anthropic when using Bedrock, excellent instruction following and reasoning, supports 200K context window for large documents, streaming responses
  - **Model Selection**: Sonnet for complex reasoning tasks, Haiku for faster/cheaper queries

### Embedding Model
- **Amazon Bedrock - Titan Embeddings V2**
  - **Rationale**: HIPAA-eligible under AWS BAA, produces 1024-dimensional vectors suitable for healthcare text, optimized for retrieval tasks, cost-effective compared to third-party APIs
  - **Alternatives Considered**: OpenAI embeddings (not HIPAA-eligible), self-hosted models (requires GPU infrastructure)

### Document Processing
- **PyPDF2** or **pdfplumber** (Python)
  - **Rationale**: Pure Python libraries for PDF text extraction, handle most clinical document formats, no external services required
- **pdf-parse** (Node.js)
  - **Rationale**: Lightweight PDF parsing for JavaScript, handles standard PDF formats

### Text Chunking
- **LangChain** 
  - **Rationale**: LangChain provides text splitters optimized for LLM context windows, handles recursive chunking with overlap for better retrieval, actively maintained

## Authentication & Authorization

### Authentication Framework
- **OIDC/SAML Integration**
  - **Rationale**: Enterprise healthcare organizations use identity providers (Okta, Auth0, Azure AD), OIDC/SAML enables SSO and MFA enforcement, meets HIPAA unique user identification requirements

### Identity Providers
- **AWS Cognito**
  - **Rationale**: Supports MFA, RBAC, and audit logging required for HIPAA, customers can use their existing IdP

### Session Management
- **JWT (JSON Web Tokens)**
  - **Rationale**: Stateless authentication suitable for distributed systems, can embed tenant context in claims, short expiration times (15-60 min) with refresh tokens for security

### MFA Enforcement
- **IdP-Level MFA** (TOTP, SMS, Push Notifications)
  - **Rationale**: HIPAA requires MFA for access to ePHI, delegating to IdP ensures consistent enforcement and audit trail

## Encryption & Key Management

### Encryption Key Management
- **AWS KMS (Key Management Service)**
  - **Rationale**: HIPAA-eligible, provides HSM-backed key generation and storage, supports customer-managed keys (CMK), automatic key rotation, audit trail via CloudTrail, integrates with S3 and RDS

### Per-Tenant Key Strategy
- **Individual CMKs per Tenant**
  - **Rationale**: Cryptographic isolation between tenants, key deletion enables secure tenant offboarding, meets stringent security requirements for healthcare SaaS

### Encryption at Rest
- **Database**: RDS encryption with KMS (AES-256)
- **Object Storage**: S3 SSE-KMS with per-tenant keys
- **Application-Level**: Sensitive fields encrypted before storage using tenant KMS key

### Encryption in Transit
- **TLS 1.2+** for all network communication
  - **Rationale**: HIPAA requires TLS 1.2 minimum, enforced on RDS connections, S3 API calls, Bedrock API calls, and application endpoints

## Testing & Quality

### Test Framework
- **pytest** (Python/FastAPI)
  - **Rationale**: Industry-standard Python testing framework, excellent fixtures and parameterization, rich plugin ecosystem (pytest-asyncio for async tests, pytest-cov for coverage)
- **Jest** (Node.js/Next.js)
  - **Rationale**: Built-in test runner for JavaScript/TypeScript, great for both unit and integration tests, snapshot testing for UI components

### Testing Strategy
- **Unit Tests**: Core business logic (encryption, document processing, RAG pipeline)
- **Integration Tests**: API endpoints with test database, authentication flows, end-to-end document ingestion
- **Security Tests**: Authorization checks, tenant isolation validation, PHI leakage prevention
- **Performance Tests**: Vector search latency, RAG response time, concurrent user load

### Linting & Formatting
- **Python**: `black` (formatting), `ruff` (linting), `mypy` (type checking)
  - **Rationale**: Black for opinionated consistent formatting, Ruff for fast linting (replaces Flake8/isort), mypy for catching type errors
- **TypeScript/JavaScript**: `prettier` (formatting), `eslint` (linting)
  - **Rationale**: Prettier for consistent code style, ESLint for catching bugs and enforcing best practices

### Code Quality Tools
- **pre-commit hooks**: Automatically run formatters and linters before commits
- **GitHub Actions**: CI pipeline for automated testing on pull requests

## Deployment & Infrastructure

### Hosting Platform
- **Railway**
  - **Rationale**: Platform-as-a-Service with HIPAA BAA available, simplifies deployment vs raw AWS, handles container orchestration, provides templates for one-click provisioning, built-in secrets management
  - **Configuration**: Railway projects connected to AWS VPC for database and S3 access

### Cloud Provider (Underlying Infrastructure)
- **AWS (Amazon Web Services)**
  - **Rationale**: Comprehensive HIPAA-eligible services, mature BAA program, widest selection of compliant services (RDS, S3, KMS, Bedrock, VPC), excellent documentation for compliance

### Infrastructure as Code
- **Terraform**
  - **Rationale**: Industry-standard IaC tool for AWS resource provisioning, declarative configuration, state management for tracking resources, enables reproducible environments
  - **Resources Managed**: VPC, subnets, security groups, RDS instances, S3 buckets, KMS keys, IAM roles

### Container Runtime
- **Docker**
  - **Rationale**: Standardized containerization for consistent development and production environments, Railway natively supports Docker deployment

### CI/CD
- **GitHub Actions**
  - **Rationale**: Native integration with GitHub repositories, free for public repos and generous free tier for private repos, flexible workflow configuration, supports matrix builds for testing multiple environments

### Networking
- **AWS VPC (Virtual Private Cloud)**
  - **Rationale**: Network isolation for HIPAA compliance, private subnets for database and Retool, public subnets for application servers with restricted security groups
  - **Configuration**: NAT Gateway for outbound internet access from private subnets, Network ACLs for additional security layer

## Third-Party Services

### Monitoring & Logging
- **Application Logs**: Structured logging to AWS CloudWatch Logs
  - **Rationale**: Centralized log aggregation, HIPAA-eligible, retention policies for compliance, searchable with CloudWatch Insights
- **Performance Monitoring**: AWS CloudWatch Metrics
  - **Rationale**: Built-in metrics for RDS, S3, and application performance, custom metrics for RAG pipeline latency

### Error Tracking
- **AWS CloudWatch Alarms** 
  - **Rationale**: CloudWatch for basic alerting

### Audit Trail
- **AWS CloudTrail**
  - **Rationale**: Tracks all AWS API calls for compliance auditing, immutable log storage in S3, integration with CloudWatch for real-time alerting

### Secrets Management
- **Railway Environment Variables** + **AWS Secrets Manager**
  - **Rationale**: Railway for deployment-time secrets, AWS Secrets Manager for runtime secrets (database passwords, API keys), automatic rotation support

## Development Tools

### Version Control
- **Git** with **GitHub**
  - **Rationale**: Industry standard, excellent collaboration features, integrates with CI/CD

### Local Development
- **Docker Compose**
  - **Rationale**: Local development environment matching production (PostgreSQL with pgvector, localstack for S3 simulation), consistent across team members

### API Documentation
- **FastAPI**: Auto-generated OpenAPI/Swagger UI

### Database Migrations
- **Alembic** (Python/SQLAlchemy)
  - **Rationale**: Migration tool for SQLAlchemy, version-controlled database schema changes

## Compliance-Specific Technologies

### Audit Logging
- **Custom Audit Log Table** (PostgreSQL)
  - **Rationale**: Application-level audit logs capture business logic events (data access, modifications) that infrastructure logs miss, immutable append-only table, indexed for fast queries

### PHI Detection
- **Regex Patterns** + **spaCy** (optional NLP)
  - **Rationale**: Regex for detecting SSN, MRN, dates; spaCy for named entity recognition (person names, locations) in de-identification workflows

### Access Control
- **Casbin** (policy engine)
  - **Rationale**: Casbin provides flexible policy-based access control, supports multiple access control models (RBAC, ABAC), external policy storage

### Tenant Isolation Middleware
- **Custom Middleware**
  - **Rationale**: Framework-specific middleware (FastAPI middleware) extracts tenant context from JWT claims, validates tenant access, injects tenant filter into database queries

## Architecture Decision Records

### Why Bedrock Over OpenAI?
OpenAI does not offer a HIPAA BAA, making it unsuitable for processing PHI. Bedrock provides equivalent LLM capabilities (via Claude) with AWS BAA coverage.

### Why pgvector Over Dedicated Vector Database?
Reduces infrastructure complexity and cost. For MVP scale (tens of thousands of documents), pgvector performance is sufficient. Can migrate to dedicated vector DB (e.g., Pinecone with BAA) if scale demands it.

### Why Self-Hosted Retool Over Retool Cloud?
Retool Cloud does not offer HIPAA BAA. Self-hosting within customer VPC ensures all PHI stays within BAA-covered infrastructure.

### Why Railway Over Direct AWS?
Railway simplifies deployment and provides BAA coverage while using AWS infrastructure underneath. Reduces DevOps complexity for developers. Alternative: Use AWS ECS/Fargate directly for more control at cost of complexity.

### Why KMS Per-Tenant Keys?
Provides cryptographic isolation between tenants, not just logical. Enables secure tenant offboarding by destroying keys. Meets requirements of healthcare enterprises with stringent security policies.

## Future Considerations

### Potential Additions (Post-MVP)
- **Redis/ElastiCache**: Session storage and caching for performance optimization
- **Amazon OpenSearch**: Advanced analytics on audit logs and document metadata
- **AWS WAF**: Web Application Firewall for DDoS protection and attack mitigation
- **Amazon Macie**: Automated PHI discovery and classification in S3 buckets
- **Step Functions**: Orchestration for complex multi-step document processing workflows

### Scalability Path
- **Read Replicas**: RDS read replicas for analytics queries
- **Dedicated Vector DB**: Migration to Pinecone or Weaviate if vector search becomes bottleneck
- **CDN**: CloudFront for serving static assets with TLS
- **Multi-Region**: Active-active deployment for disaster recovery and global latency reduction
