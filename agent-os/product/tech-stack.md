# Tech Stack

## Overview

This document outlines all technology choices for the **HIPAA-Compliant Railway + AWS Scaffold** - a production-ready application scaffold for deploying AI-enabled, HIPAA-compliant healthcare applications with low-code UI capabilities. All technology selections enforce the **Railway as Orchestrator + AWS as Data Plane** architectural pattern where:

- **Railway** hosts stateless application containers (FastAPI backend, Retool frontend) and automates AWS infrastructure provisioning via Terraform
- **AWS** provides all HIPAA-eligible data services (RDS PostgreSQL, S3 storage, KMS encryption, Bedrock AI, VPC networking) where PHI resides exclusively
- **Terraform** Infrastructure as Code modules provision VPC, RDS, S3, KMS, IAM policies, security groups, and networking - included in scaffold
- **VPC Networking** connects Railway-hosted containers to AWS data plane via VPC peering or PrivateLink (PHI never transits public internet)

**Core Principle**: All PHI must reside within AWS services covered by comprehensive BAA. Railway containers are stateless and cannot store PHI locally. Scaffold enforces this boundary through networking configuration, IAM policies, and application-level controls.

---

## Infrastructure & Deployment

### Infrastructure as Code
- **Terraform**
  - **Rationale**: Industry-standard IaC tool for AWS resource provisioning with declarative configuration, state management, and reproducible environments. Scaffold includes production-ready modules for all AWS resources.
  - **Modules Included**: `vpc.tf` (VPC, subnets, NAT gateway, VPC endpoints), `rds.tf` (PostgreSQL with pgvector, Multi-AZ, encryption), `s3.tf` (encrypted buckets, versioning, lifecycle policies), `kms.tf` (master keys, per-tenant aliases), `iam.tf` (roles/policies with least privilege), `networking.tf` (security groups, VPC peering/PrivateLink), `config.tf` (AWS Config rules for drift detection)
  - **Execution Model**: Railway template triggers `terraform apply` during deployment - zero manual AWS console work required

### Cloud Provider (Data Plane)
- **AWS (Amazon Web Services)**
  - **Rationale**: Comprehensive HIPAA-eligible services with mature BAA program, widest selection of compliant services (RDS, S3, KMS, Bedrock, VPC), excellent compliance documentation
  - **Services Used**: RDS PostgreSQL (database), S3 (object storage), KMS (encryption keys), Bedrock (AI/LLM), VPC (networking isolation), CloudWatch (logging/monitoring), CloudTrail (audit trail), AWS Config (drift detection), IAM (access control)
  - **BAA Coverage**: All services used in scaffold are HIPAA-eligible with comprehensive AWS BAA coverage

### Hosting Platform (Orchestrator)
- **Railway**
  - **Rationale**: Platform-as-a-Service simplifies deployment orchestration vs raw AWS ECS/Fargate, handles container orchestration, provides one-click template provisioning, automates Terraform execution, built-in secrets management
  - **What Railway Hosts**: FastAPI backend containers (stateless, no PHI storage), Retool frontend containers (future feature), application deployment automation
  - **Railway Template**: `railway.json` defines services, environment variables, and post-deploy hooks to trigger Terraform provisioning
  - **Railway BAA**: Available on Pro plan, covers Railway platform only (not data services) - PHI must stay in AWS

### Networking & PHI Boundary

This is the **most critical** component for HIPAA compliance - enforcing that PHI never leaves AWS's secure boundary.

- **AWS VPC (Virtual Private Cloud)**
  - **Rationale**: Network isolation for HIPAA compliance, private subnets for RDS and Retool, public subnets for application ingress with restricted security groups
  - **Configuration**: VPC with CIDR block, 3 availability zones, public subnets (NAT gateway, internet gateway), private subnets (RDS, Retool), route tables, network ACLs
  - **Terraform Automation**: Complete VPC provisioned by scaffold - developers never touch AWS console networking

- **VPC Peering or PrivateLink** (Railway to AWS)
  - **Rationale**: Secure private connection between Railway-hosted containers and AWS VPC - PHI data flows never transit public internet
  - **Options**:
    - VPC Peering (if Railway provides VPC peering capability)
    - PrivateLink/VPC Endpoints (if Railway connects via AWS PrivateLink)
    - Alternatively: Encrypted TLS connections over public internet with strict IAM policies (least secure, but simplest if Railway doesn't support private networking)
  - **Configuration**: Security groups restrict inbound traffic to RDS only from application IAM role, S3 VPC endpoints for private S3 access

- **Security Groups & Network ACLs**
  - **Rationale**: Defense-in-depth network security - security groups control instance-level traffic, network ACLs control subnet-level traffic
  - **Configuration**:
    - RDS security group allows PostgreSQL port only from application IAM role/IP ranges
    - S3 VPC endpoint restricts access to application IAM role only
    - Outbound rules block unauthorized destinations (prevent PHI exfiltration)
  - **Terraform Automation**: All security groups and NACLs provisioned by scaffold with least-privilege rules

### Container Runtime
- **Docker**
  - **Rationale**: Standardized containerization for consistent development and production environments, Railway natively supports Docker deployment from Dockerfile
  - **Configuration**: Multi-stage Dockerfile included in scaffold for optimized production builds

### CI/CD
- **GitHub Actions**
  - **Rationale**: Native integration with GitHub repositories, free for public repos and generous free tier for private repos, flexible workflow configuration
  - **Scaffold Includes**: `.github/workflows/` with Terraform validation (`terraform fmt`, `terraform validate`, `tflint`), security checks (S3 encryption verification, IAM policy auditing), test suite execution, drift detection checks

---

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
- **AWS RDS PostgreSQL 15+ with pgvector**
  - **Rationale**: HIPAA-eligible under AWS BAA with comprehensive coverage, pgvector extension supported, enterprise-grade reliability, automated backups with point-in-time recovery, encryption at rest with AWS KMS, encryption in transit with TLS 1.2+, mature compliance program
  - **Configuration**: Provisioned automatically by Railway template via Terraform, TLS 1.2+ enforced, automated daily backups with 30-day retention (HIPAA requirement), connection pooling via application layer (SQLAlchemy), Multi-AZ deployment for production
  - **Template Automation**: Railway template includes Terraform modules that provision RDS instance with security groups, parameter groups, and subnet configuration - zero manual AWS console work

### Vector Database Extension
- **pgvector**
  - **Rationale**: Native PostgreSQL extension eliminates need for separate vector database, reduces infrastructure complexity, supports cosine similarity and L2 distance for semantic search, scales to millions of vectors, available on AWS RDS PostgreSQL

### Object Storage
- **AWS S3**
  - **Rationale**: HIPAA-eligible under AWS BAA with comprehensive coverage, enterprise-grade durability (99.999999999%), server-side encryption with KMS for per-tenant encryption keys, versioning for data recovery, lifecycle policies for cost optimization, access logging for audit trails
  - **Configuration**: Provisioned automatically by Railway template via Terraform, server-side encryption with KMS (SSE-KMS), versioning enabled, bucket policies restricting access to application IAM roles only, access logging enabled to dedicated audit bucket, VPC endpoint for private access (no public internet transit)
  - **Template Automation**: Railway template includes Terraform modules that create S3 buckets with encryption, versioning, VPC endpoint configuration, and access policies pre-configured
  - **PHI Boundary**: Application accesses S3 via AWS SDK with IAM role credentials - Railway containers never download PHI to local filesystem

### ORM/Query Builder
- **SQLAlchemy 2.0** (for Python/FastAPI)
  - **Rationale**: Mature ORM with async support, flexible for both ORM and raw SQL, excellent for complex queries, strong type hinting with SQLAlchemy 2.0

## AI & Machine Learning (AWS BAA Boundary)

All AI/ML components run within AWS's HIPAA-eligible boundary. PHI never leaves AWS services.

### Large Language Model
- **Amazon Bedrock - Claude 3.5 Sonnet or Claude 3 Haiku**
  - **Rationale**: HIPAA-eligible under AWS BAA, no data retention by Anthropic when using Bedrock, excellent instruction following and reasoning, supports 200K context window for large documents, streaming responses
  - **Model Selection**: Sonnet for complex reasoning tasks, Haiku for faster/cheaper queries
  - **PHI Boundary**: Application calls Bedrock API from Railway container via AWS SDK with IAM credentials - PHI in prompts stays within AWS, responses streamed back to application

### Embedding Model
- **Amazon Bedrock - Titan Embeddings V2**
  - **Rationale**: HIPAA-eligible under AWS BAA, produces 1024-dimensional vectors suitable for healthcare text, optimized for retrieval tasks, cost-effective compared to third-party APIs
  - **Alternatives Considered**: OpenAI embeddings (not HIPAA-eligible), self-hosted models (requires GPU infrastructure)
  - **PHI Boundary**: Document text sent to Bedrock for embedding generation stays within AWS, embeddings stored directly in RDS PostgreSQL (AWS)

### Document Processing
- **PyPDF2** or **pdfplumber** (Python)
  - **Rationale**: Pure Python libraries for PDF text extraction, handle most clinical document formats, no external services required, processing happens in Railway container memory (stateless - documents not persisted locally)
  - **Scaffold Includes**: Document processing service that downloads PDFs from S3, extracts text in memory, uploads chunks back to S3, stores metadata in RDS - zero local persistence

### Text Chunking
- **LangChain**
  - **Rationale**: LangChain provides text splitters optimized for LLM context windows, handles recursive chunking with overlap for better retrieval, actively maintained
  - **Scaffold Includes**: Chunking utilities tuned for medical documents (500-1000 tokens per chunk), overlap configuration for context preservation

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
  - **Rationale**: HIPAA-eligible under AWS BAA, provides HSM-backed key generation and storage, supports customer-managed keys (CMK), automatic key rotation, audit trail via CloudTrail, integrates with RDS and S3
  - **Template Automation**: Railway template includes Terraform modules that provision KMS master keys with appropriate key policies

### Per-Tenant Key Strategy
- **Individual CMKs per Tenant**
  - **Rationale**: Cryptographic isolation between tenants, key deletion enables secure tenant offboarding, meets stringent security requirements for healthcare SaaS
  - **Configuration**: Application automatically provisions per-tenant keys on tenant creation using AWS KMS API

### Encryption at Rest
- **Database**: AWS RDS encryption with KMS (AES-256), enforced by default in Terraform templates
- **Object Storage**: AWS S3 SSE-KMS with per-tenant keys, automatically configured by Terraform
- **Application-Level**: Sensitive fields encrypted before storage using tenant KMS key (optional additional layer)

### Encryption in Transit
- **TLS 1.2+** for all network communication
  - **Rationale**: HIPAA requires TLS 1.2 minimum, enforced on RDS connections, S3 API calls, Bedrock API calls, and application endpoints (Railway-hosted)

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
- **Scaffold Includes**: `.github/workflows/` with test execution, Terraform validation, security checks

---

## Compliance & Monitoring

### Monitoring & Logging
- **Application Logs**: Structured logging to AWS CloudWatch Logs
  - **Rationale**: Centralized log aggregation, HIPAA-eligible under AWS BAA, retention policies for compliance (30+ days for HIPAA), searchable with CloudWatch Insights
  - **Configuration**: Application exports structured JSON logs to CloudWatch, automatically configured by Terraform

- **Railway Logs**: Application container logs
  - **Rationale**: Real-time log streaming for Railway-hosted application containers, useful for debugging deployments, complementary to CloudWatch for infrastructure logs
  - **Use Case**: Developer debugging, deployment monitoring, application startup issues

- **Performance Monitoring**: AWS CloudWatch Metrics
  - **Rationale**: Built-in metrics for RDS (query performance, connections), S3 (request rates, storage), and application performance, custom metrics for RAG pipeline latency
  - **Configuration**: RDS and S3 metrics automatically collected, application custom metrics published via AWS SDK

### Error Tracking
- **AWS CloudWatch Alarms**
  - **Rationale**: Automated alerting for AWS service health (RDS CPU/memory, S3 access errors), custom alerts for application metrics (RAG latency, authentication failures)
  - **Configuration**: Alert rules configured in Terraform, notifications via SNS to email/Slack

### Audit Trail
- **Application Audit Logs**: PostgreSQL audit_logs table
  - **Rationale**: Database audit_logs table captures all business logic events (data access, modifications), immutable append-only design, queryable via API for compliance reporting
  - **Configuration**: Audit triggers automatically created by Alembic migrations

- **AWS CloudTrail**
  - **Rationale**: Tracks all AWS API calls for compliance auditing (RDS configuration changes, S3 access, KMS key usage), immutable log storage in S3, integration with CloudWatch for real-time alerting
  - **Configuration**: CloudTrail enabled via Terraform, logs stored in dedicated S3 audit bucket with versioning and lifecycle policies

- **Railway Audit Logs**
  - **Rationale**: Railway tracks application deployment events (container deployments, environment variable updates, rollbacks) for change management
  - **Use Case**: Tracking application deployment history, correlating infrastructure changes with application behavior

### Secrets Management
- **Railway Environment Variables** + **AWS Secrets Manager**
  - **Rationale**: Railway for deployment-time secrets (AWS credentials, OIDC configuration), AWS Secrets Manager for runtime secrets (database passwords, API keys), automatic rotation support
  - **Configuration**: Terraform provisions Secrets Manager secrets, Railway environment variables reference secret ARNs, application retrieves secrets at runtime

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

### Why Railway Over Direct AWS Deployment?
Railway simplifies deployment orchestration while using AWS infrastructure for data services. Railway hosts the application containers and automates Terraform execution for AWS provisioning (RDS, S3, VPC, KMS). This reduces DevOps complexity compared to manually setting up AWS ECS/Fargate, load balancers, and CI/CD pipelines. The template provides one-click deployment that would otherwise require weeks of infrastructure engineering. Alternative: Use AWS ECS/Fargate directly for more control at cost of complexity.

### Why KMS Per-Tenant Keys?
Provides cryptographic isolation between tenants, not just logical. Enables secure tenant offboarding by destroying keys. Meets requirements of healthcare enterprises with stringent security policies.

### Why Enforce PHI Boundary Between Railway and AWS?
HIPAA compliance requires that PHI resides only within BAA-covered services. While Railway offers BAA, AWS provides more comprehensive coverage with mature compliance programs for data services (RDS, S3, KMS). By enforcing architectural separation where Railway hosts stateless application containers and AWS hosts all PHI data, we minimize compliance risk and provide clear audit boundaries. VPC networking, IAM policies, and application-level controls enforce this boundary - developers cannot accidentally store PHI in Railway containers even if bugs exist in application code.

### Why Include AWS Config for Drift Detection?
Infrastructure drift (manual AWS console changes, misconfigured resources) can violate HIPAA compliance without triggering alarms. AWS Config rules continuously monitor infrastructure state and alert on violations (unencrypted S3 buckets, overly permissive IAM policies, public RDS endpoints). This provides continuous compliance verification beyond deployment-time checks, enabling rapid remediation before audits detect violations.

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
