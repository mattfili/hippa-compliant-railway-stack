# Product Roadmap

## Overview

This roadmap outlines the development path for building a production-ready **HIPAA-compliant application scaffold** deployable via Railway template. The scaffold enforces the **Railway as Orchestrator + AWS as Data Plane** architectural pattern where Railway hosts stateless application containers and AWS provides all HIPAA-eligible data services (RDS, S3, KMS, Bedrock).

Features are ordered to build foundational infrastructure first (Terraform modules, VPC networking, AWS resources), then layer on application logic (authentication, multi-tenant data model, RAG pipeline), compliance features (audit logging, PHI detection), and developer experience (Retool UI, documentation).

**Core Philosophy**:
- **Scaffold, not SaaS**: Developers clone this repo and extend it for their healthcare application - it's a starting point, not a finished product
- **Infrastructure as Code First**: AWS infrastructure (VPC, RDS, S3, KMS, IAM, networking) provisioned via Terraform modules included in scaffold
- **PHI Boundary Enforcement**: All PHI resides exclusively within AWS BAA-covered services - Railway containers are stateless and cannot store PHI locally
- **One-Click Deployment**: Railway template automates Terraform execution and application deployment - zero manual AWS console work required

## Ordered Feature Checklist

1. [x] **Backend API Scaffold with Authentication** — FastAPI application with route structure, OIDC/SAML authentication integration with MFA support, JWT token handling, and basic health check endpoints. Includes tenant context middleware that extracts and validates tenant ID from authenticated requests. `M`

2. [x] **Database Schema and Multi-Tenant Data Model** — PostgreSQL schema with tenant isolation patterns, pgvector extension setup, core tables (tenants, users, documents, audit_logs), foreign key relationships, and database migrations framework. Includes indexes optimized for tenant-scoped queries. Database migrations run automatically on deployment. `M`

3. [x] **AWS Infrastructure Provisioning (Terraform Modules)** — Complete Infrastructure as Code implementation for all AWS resources required for HIPAA compliance. Includes:
   - **VPC & Networking**: VPC with public/private subnets across 3 AZs, NAT gateway, internet gateway, route tables, network ACLs, VPC endpoints for S3/RDS private access, VPC peering/PrivateLink configuration for Railway connectivity
   - **RDS PostgreSQL**: Multi-AZ deployment with pgvector extension, encryption at rest with KMS, TLS 1.2+ enforcement, automated backups (30-day retention), security groups restricting access to application IAM role only, parameter groups for HIPAA compliance settings
   - **S3 Buckets**: Encrypted buckets for documents (SSE-KMS with per-tenant keys), versioning enabled, lifecycle policies for cost optimization, bucket policies restricting access to application IAM role, VPC endpoint access only (no public access), access logging to audit bucket
   - **KMS Keys**: Master key for infrastructure encryption, per-tenant key aliases for data encryption, key policies with least privilege, automatic rotation enabled, CloudTrail logging for all key operations
   - **IAM Roles & Policies**: Application IAM role with scoped permissions (RDS read/write, S3 read/write to specific buckets, KMS encrypt/decrypt with specific keys, Bedrock InvokeModel), service roles for RDS/Lambda, policies following principle of least privilege
   - **Security Groups**: RDS security group (allow PostgreSQL port only from application), application security group (allow outbound to RDS/S3/Bedrock only), restrictive egress rules to prevent PHI exfiltration
   - **AWS Config Rules**: Drift detection for unencrypted S3 buckets, overly permissive IAM policies, public RDS endpoints, disabled CloudTrail, non-compliant security group rules
   - **Railway Integration**: Environment variable templates for Railway services, IAM role assumption configuration, networking setup for VPC connectivity
   - **Template Automation**: `railway.json` triggers Terraform apply during deployment, state management configuration, output variables for application connection strings
   This is the most infrastructure-heavy feature - expect 2+ weeks for complete implementation and testing. `XL`

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

18. [ ] **Railway Template Configuration and Publishing** — Finalize railway.json with service definitions and post-deploy hooks, environment variable templates with secure defaults, startup scripts for database initialization and migrations, health check configuration, resource allocation settings, and template documentation for one-click deployment. Publish template to Railway marketplace with clear instructions for AWS credential configuration. **Note**: Most Railway configuration is completed in Feature 3 - this feature polishes and publishes. `S`

## Effort Scale

- **XS**: 1 day - Small, isolated changes
- **S**: 2-3 days - Single feature or service
- **M**: 1 week - Moderate complexity with integration
- **L**: 2 weeks - Complex feature requiring multiple services
- **XL**: 3+ weeks - Major architectural component

## Development Notes

### Dependencies and Sequencing

- **Feature 3 is the critical path**: AWS Infrastructure Provisioning must be completed before most other features can be fully functional. All subsequent features that interact with AWS services (RDS, S3, KMS, Bedrock) require the Terraform modules and VPC networking from Feature 3.
- **Features 1-2** (completed): Backend API scaffold and database schema provide application foundation
- **Feature 3** (AWS Infrastructure): Blocks Features 4-9, 11 (all require AWS resources)
- **Feature 4** (tenant encryption) must be completed before Feature 5 (document storage) to ensure data is encrypted from first upload
- **Features 5-7** (ingestion, processing, embedding) form the document pipeline and should be completed sequentially
- **Feature 8-9** (search, RAG) depend on the document pipeline and can begin once embeddings are available
- **Feature 11-12** (Retool in VPC) require Feature 3 (VPC networking) but can be developed in parallel with Features 8-10
- **Feature 17** (testing) should be developed incrementally alongside features, not saved for the end, with heavy focus on testing Feature 3 infrastructure provisioning
- **Feature 18** (Railway template publishing) is the final polish step after all other features are complete

### Prioritization Strategy

The roadmap prioritizes **infrastructure-first, then application logic**. Feature 3 (AWS Infrastructure Provisioning) is the largest single feature and the critical path - without it, developers cannot deploy a functional scaffold. Once infrastructure is in place, we layer on application features (authentication, data model, RAG pipeline), compliance guardrails (audit logging, drift detection), and developer experience (Retool UI, documentation).

This approach ensures developers can deploy a working scaffold early (after Feature 3) and incrementally add features on top of a proven foundation. The scaffold is designed to be extended, not used as-is - developers will customize RAG prompts, add domain-specific UI, and integrate with their existing systems.

### Phase Groupings

While features should be completed in order, they can be conceptually grouped into phases:

- **Phase 1 (Infrastructure Scaffold)**: Features 1-3 - Backend API, database schema, AWS infrastructure provisioning via Terraform (VPC, RDS, S3, KMS, IAM, networking, AWS Config). **This is the foundation - expect 3-4 weeks of work**.
- **Phase 2 (Data Encryption & Storage)**: Features 4-5 - Per-tenant KMS keys, document ingestion to S3 with encryption
- **Phase 3 (AI/RAG Pipeline)**: Features 6-9 - PDF processing, Bedrock embeddings, pgvector search, Claude response generation
- **Phase 4 (Compliance & Auditing)**: Features 10, 14, 16 - Audit logging, PHI detection, anomaly detection
- **Phase 5 (Low-Code UI)**: Features 11-13 - Retool in VPC, pre-built dashboards, RBAC
- **Phase 6 (Testing & Publishing)**: Features 15, 17-18 - Documentation, automated tests, Railway template publishing

### MVP Scaffold Definition

A minimum viable scaffold includes Features 1-10, which provides:

- **Infrastructure Scaffold** (Feature 3): Terraform modules for VPC, RDS, S3, KMS, IAM, networking, AWS Config - deployable via Railway template
- **Application Scaffold**: FastAPI backend with authentication, multi-tenant data model, Row-Level Security policies
- **RAG Scaffold**: Complete document intelligence pipeline (S3 ingestion, PDF processing, Bedrock embeddings, pgvector search, Claude responses)
- **Compliance Scaffold**: Immutable audit logs, database triggers, CloudTrail integration

This MVP scaffold enables developers to:
1. Deploy infrastructure to AWS via one-click Railway template
2. Extend the scaffold with domain-specific features (custom UI, additional API endpoints, specialized RAG prompts)
3. Pass HIPAA audits by starting from a compliant foundation
4. Validate value before investing in low-code UI layer (Features 11-13)

**Note**: The MVP is a scaffold, not a finished application. Developers will customize it for their specific healthcare use case.
