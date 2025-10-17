# Product Mission

## Pitch

**HIPAA-Compliant Railway + AWS Scaffold** is a production-ready application scaffold that enables developers to rapidly deploy AI-enabled, HIPAA-compliant healthcare applications with low-code UI capabilities through a one-click Railway template. Railway orchestrates deployment and hosts application containers while automatically provisioning compliant AWS infrastructure (RDS PostgreSQL with pgvector, S3 encrypted storage, KMS per-tenant encryption, VPC networking) via Terraform. All PHI resides exclusively within AWS's HIPAA-eligible boundary under comprehensive BAA coverage, while developers build features on top of a secure, multi-tenant foundation with built-in RAG capabilities, immutable audit logging, and Retool-based low-code UI extensibility.

## Users

### Primary Customers

- **Healthcare Application Developers**: Software engineers and development teams building patient-facing applications, clinical decision support tools, or healthcare data platforms that require HIPAA compliance
- **Healthcare Technology Startups**: Early-stage companies building innovative healthcare solutions who need to achieve compliance quickly without deep regulatory expertise
- **Enterprise Healthcare IT Teams**: Internal development teams at hospitals, health systems, and healthcare organizations modernizing legacy systems
- **Healthcare Data Science Teams**: ML engineers and data scientists building AI-powered healthcare applications with document processing and semantic search requirements

### User Personas

**Sarah Chen, Full-Stack Developer** (28-35)
- **Role:** Lead Engineer at a healthcare startup building a patient engagement platform
- **Context:** Small team (3-5 developers) with tight deadlines and limited DevOps resources
- **Pain Points:** Spent 6+ months researching HIPAA requirements, unsure if architecture is truly compliant, struggling to integrate LLM capabilities securely, overwhelmed by VPC networking and IAM policy complexity, can't figure out how to wire Railway app to AWS data services
- **Goals:** Start from a working scaffold that handles infrastructure provisioning, focus on product features rather than compliance plumbing, sleep well knowing PHI stays within AWS BAA boundary

**Marcus Rodriguez, Healthcare IT Architect** (35-45)
- **Role:** Senior Solutions Architect at a regional hospital system
- **Context:** Managing multiple internal applications, responsible for compliance audits, working with offshore development teams
- **Pain Points:** Each new application requires rebuilding VPC networking, IAM policies, and encryption architecture from scratch, inconsistent security patterns across projects, difficult to maintain audit trails, expensive to hire specialized AWS + HIPAA expertise, struggle to enforce PHI boundary between app and data layers
- **Goals:** Standardize on a reference scaffold with proven compliance patterns, reduce time-to-market for internal tools from months to weeks, pass audits with confidence by starting from audited infrastructure, enable less experienced developers to build compliant apps without deep AWS expertise

**Dr. Priya Patel, Clinical Informatics Lead** (40-50)
- **Role:** Physician and healthcare data analyst at a research institution
- **Context:** Building tools for clinical research with limited technical staff, needs to process medical documents and extract insights with AI
- **Pain Points:** Can't use mainstream cloud AI services due to BAA requirements, manual document review is time-consuming, existing EMR systems don't support custom workflows, no time to learn Terraform or AWS networking, compliance blocks innovation
- **Goals:** Deploy a working AI-enabled application from a scaffold in hours not months, leverage Bedrock for document analysis while maintaining compliance, empower clinical staff to customize Retool interfaces without writing code or touching infrastructure

## The Problem

### AWS Infrastructure Provisioning is Overwhelming for Healthcare Apps

Building HIPAA-compliant infrastructure on AWS requires deep expertise in VPC networking, IAM policies, KMS encryption, RDS configuration, S3 bucket policies, security groups, and VPC peering/PrivateLink. Teams spend 6-12 months learning Terraform, debugging networking issues, and navigating AWS's 200+ services to identify which are HIPAA-eligible. Even experienced DevOps engineers struggle to wire together compliant infrastructure that enforces the PHI boundary while maintaining least-privilege access controls.

**Our Solution:** Production-ready Terraform modules that provision all required AWS infrastructure (VPC, RDS with pgvector, encrypted S3, KMS keys, IAM roles, VPC networking) automatically via Railway template deployment. Start building features on day one instead of spending months on infrastructure.

### Enforcing PHI Boundary Between App and Data Layers is Complex

Healthcare applications must guarantee that PHI never leaves AWS's HIPAA-eligible boundary, even when application containers run on external platforms like Railway. This requires sophisticated networking (VPC peering, PrivateLink, security groups), IAM policies scoped to specific resources, KMS envelope encryption, and continuous drift detection to catch misconfigurations. Teams struggle to implement these controls correctly, risking BAA violations and audit failures.

**Our Solution:** Architecture-enforced PHI boundary where Railway hosts stateless application containers while all PHI resides exclusively in AWS (RDS, S3, KMS). Scaffold includes VPC networking configuration, IAM roles with least privilege, and AWS Config rules for drift detection. Developers cannot accidentally violate the boundary.

### Multi-Tenant Apps Need Per-Tenant Encryption + Isolation

Healthcare SaaS applications serve multiple healthcare organizations with strict requirements for cryptographic isolation. Simply separating data by tenant ID is insufficient - each tenant's data must be encrypted with unique AWS KMS keys, tenant context must be enforced in middleware, database Row-Level Security policies must prevent cross-tenant queries, and audit trails must prove no data leakage. Building this infrastructure requires expertise in KMS envelope encryption, SQLAlchemy middleware, and PostgreSQL RLS.

**Our Solution:** Scaffold includes complete multi-tenant architecture with per-tenant KMS keys, tenant context middleware that enforces `tenant_id` filtering, Row-Level Security policies on all tables, and immutable audit logs that capture every data access with tenant context. Tenant isolation is enforced at multiple layers (application, database, encryption).

### AI-Enabled Healthcare Apps Lack Compliant RAG Scaffolds

Healthcare organizations need to extract insights from medical documents using AI, but mainstream RAG solutions violate HIPAA by sending PHI to non-compliant APIs (OpenAI, Pinecone). Building a compliant RAG pipeline requires integrating AWS Bedrock (Claude + Titan embeddings), pgvector on RDS for semantic search, S3 for document storage, and securing all data flows within AWS's HIPAA boundary. Teams spend months debugging embedding pipelines, vector search performance, and prompt engineering.

**Our Solution:** Complete RAG scaffold with S3 document ingestion, PDF parsing, Titan Embeddings via Bedrock, pgvector semantic search on RDS PostgreSQL, and Claude-powered response generation. All components run within AWS BAA coverage with PHI never leaving the secure boundary. Developers extend the scaffold instead of building from scratch.

### Low-Code UI Requires Self-Hosting in Secure VPC

Healthcare organizations want to empower clinical staff to customize interfaces without code, but Retool Cloud cannot be used with PHI due to lack of BAA. Self-hosting Retool in AWS VPC requires configuring networking, database connections, authentication, and security hardening that most teams lack expertise to implement safely. Teams either skip low-code capabilities or spend weeks configuring Retool infrastructure.

**Our Solution:** Scaffold includes Retool deployment configuration within AWS VPC (automatically provisioned by Railway template) with pre-built dashboards for audit logs, patient records, and document analysis. Clinical staff can customize interfaces via drag-and-drop while all data stays within AWS BAA boundary.

## Differentiators

### Production-Ready Scaffold, Not Tutorial Code

Unlike basic tutorials or proof-of-concept demos, this scaffold provides production-grade infrastructure code (Terraform modules), application code (FastAPI with tenant middleware, SQLAlchemy models with RLS), and compliance guardrails (AWS Config rules, immutable audit logs, PHI boundary enforcement). The scaffold is designed to be extended, not rewritten. Developers clone the repo, deploy via Railway template, and start building features on top of a proven foundation instead of spending 6 months building infrastructure from scratch.

### Railway Orchestrator + AWS Data Plane Architecture

Unlike monolithic cloud deployments where app and data live in the same environment, this scaffold enforces separation between orchestration (Railway) and data plane (AWS). Railway hosts stateless application containers and automates Terraform execution for infrastructure provisioning, while all PHI resides exclusively within AWS's HIPAA-eligible boundary (RDS, S3, KMS). This architecture prevents accidental PHI leakage to non-compliant services while simplifying deployment orchestration.

### Infrastructure as Code with Compliance Guardrails

Unlike manual AWS console clicking or ad-hoc scripts, this scaffold includes production-ready Terraform modules that provision VPC networking, RDS PostgreSQL with pgvector, encrypted S3 buckets, KMS keys, IAM roles with least privilege, and VPC peering/PrivateLink for secure connectivity. AWS Config rules detect drift from compliant configurations (e.g., unencrypted S3 buckets, overly permissive IAM policies). Infrastructure changes are code-reviewed, version-controlled, and automatically tested in CI.

### Multi-Layer Tenant Isolation (App + DB + Encryption)

Unlike simple row-level filtering, this scaffold enforces tenant isolation at three layers: application middleware validates tenant context from JWT and injects `tenant_id` filters, PostgreSQL Row-Level Security policies block cross-tenant queries at the database level, and AWS KMS per-tenant encryption keys provide cryptographic isolation. Even if application bugs allow cross-tenant queries, encrypted data remains unreadable without the correct tenant's KMS key.

### Complete AI/RAG Scaffold Within AWS BAA Boundary

Unlike generic LangChain examples that use OpenAI or Pinecone (non-HIPAA), this scaffold provides end-to-end RAG pipeline using only AWS BAA-covered services: S3 for document storage, Bedrock Titan Embeddings for vector generation, RDS pgvector for semantic search, and Bedrock Claude for response generation. All data flows remain within AWS's secure boundary. Developers extend the scaffold with domain-specific prompt engineering and chunking strategies instead of building infrastructure from scratch.

### Low-Code UI in Secure VPC (Retool Self-Hosted)

Unlike Retool Cloud (no BAA), this scaffold includes configuration for self-hosted Retool deployment within AWS VPC, automatically provisioned by Railway template. Retool connects to RDS PostgreSQL via private networking (no public endpoints) and inherits tenant context from JWT. Clinical staff customize audit dashboards, patient record forms, and document analysis interfaces via drag-and-drop without writing code or touching infrastructure.

## Key Features

### Infrastructure & Deployment Scaffold

- **Terraform Modules for AWS Infrastructure:** Production-ready IaC modules provision VPC (public/private subnets, NAT gateway, VPC endpoints), RDS PostgreSQL 15 with pgvector extension (encrypted, Multi-AZ, automated backups), S3 buckets (encrypted, versioned, lifecycle policies), KMS master keys + per-tenant aliases, IAM roles/policies (least privilege, scoped to app resources), security groups and network ACLs for PHI boundary enforcement

- **Railway Template with IaC Automation:** Railway template (`railway.json`) defines application services and triggers Terraform provisioning during deployment. One-click deployment provisions all AWS infrastructure, deploys application containers to Railway, runs database migrations, and wires environment variables. Developers provide AWS credentials and OIDC config only - zero manual AWS console work required

- **VPC Networking for PHI Boundary:** Scaffold includes VPC peering or PrivateLink configuration to connect Railway-hosted application to AWS VPC securely. All PHI data flows traverse private connections (no public internet transit). Security groups restrict inbound/outbound traffic to authorized sources only. Architecture enforces that Railway containers never store PHI locally

- **AWS Config Rules for Drift Detection:** Automated compliance checks detect misconfigurations that violate HIPAA invariants (unencrypted S3 buckets, overly permissive IAM policies, public RDS endpoints, disabled CloudTrail). Config rules trigger alerts on drift, enabling rapid remediation before audits

### Application Scaffold

- **Multi-Tenant Foundation with Triple Isolation:** Tenant isolation enforced at three layers: FastAPI middleware extracts tenant context from JWT and injects `tenant_id` filters into all queries, PostgreSQL Row-Level Security policies block cross-tenant access at database level, AWS KMS per-tenant encryption keys provide cryptographic isolation (even if app bugs allow cross-tenant queries, data remains unreadable without correct key)

- **Complete RAG Pipeline (AWS BAA Only):** End-to-end document intelligence scaffold using S3 for encrypted document storage, Bedrock Titan Embeddings for vector generation, RDS pgvector for semantic search, Bedrock Claude for response generation. All components run within AWS HIPAA boundary. Scaffold includes PDF parsing, text chunking, embedding storage, similarity search queries, and prompt construction - developers extend with domain-specific logic

- **Immutable Audit Logging System:** Append-only audit log table (PostgreSQL) captures every CRUD operation, authentication event, document access, and administrative action with user ID, tenant ID, timestamp, IP address, action type, and affected resource IDs. Database triggers prevent UPDATE/DELETE on audit logs. AWS CloudTrail audits infrastructure changes (IAM, KMS, S3 bucket policies)

- **Authentication & Authorization Scaffold:** OIDC/SAML integration with JWT validation, tenant context extraction from JWT claims, role-based access control with predefined roles (admin, clinician, analyst, patient), permission checks via policy engine (Casbin), MFA enforcement at IdP level

### Low-Code UI Scaffold

- **Retool Self-Hosted in AWS VPC:** Configuration for Retool deployment within private AWS VPC subnet (auto-provisioned by Railway template), connected to RDS PostgreSQL via VPC endpoint (no public internet), authenticated via OIDC/JWT with tenant context inheritance, sample dashboards included (audit log viewer, patient record forms, document analysis UI) that clinical staff customize via drag-and-drop

- **Pre-Built Compliance Dashboards:** Retool templates for audit log filtering/export (searchable by tenant, user, date range, action type), tenant management (onboard new orgs, view usage metrics, manage encryption keys), user administration (assign roles, review permissions), document library (upload, search, view processing status)

### Extensibility & Developer Features

- **Scaffold Designed for Extension:** FastAPI route structure with clear separation of concerns (routes, services, models, middleware), SQLAlchemy models with documented relationships and constraints, utility modules for common tasks (KMS encryption, S3 upload, audit logging), comprehensive inline documentation explaining design decisions and HIPAA requirements

- **Testing Scaffold with Compliance Checks:** Unit tests for tenant isolation (attempt cross-tenant access, verify failure), encryption (verify KMS key usage, test envelope encryption), audit logs (verify immutability, test trigger enforcement), integration tests for API endpoints with test tenant data, security tests simulating PHI leakage scenarios

- **PHI Scrubbing and De-Identification Utilities:** Built-in tools for detecting and redacting Protected Health Information in documents and LLM responses using pattern matching and NLP, enabling safe data sharing with researchers or third parties

- **Key Rotation and Encryption Management:** Automated workflows for rotating tenant encryption keys, re-encrypting data with new keys, and maintaining key version history for compliance audits and disaster recovery scenarios

- **Extensible Authentication with MFA Support:** OIDC/SAML authentication framework pre-configured for common identity providers (Okta, Auth0, Azure AD) with mandatory multi-factor authentication and session management compliant with HIPAA access control requirements

- **Anomaly Detection in Audit Logs:** Machine learning-based analysis of audit logs to detect unusual access patterns (bulk data downloads, after-hours access, cross-tenant queries) with automated alerts for security teams

## Success Metrics

### Developer Adoption and Velocity

- **Time to First Compliant Deployment:** Target < 1 hour from Railway template deployment to running HIPAA-eligible scaffold with AWS infrastructure provisioned (baseline: 6-12 months building from scratch)
- **Active Scaffold Deployments:** Number of developers/teams deploying applications using this scaffold (target: 100+ teams in year one)
- **Feature Development Speed:** Percentage increase in feature velocity after starting from scaffold vs. building compliance infrastructure manually (target: 5x faster - spend 80% of time on product features instead of 80% on infrastructure)

### Compliance and Security

- **HIPAA Audit Success Rate:** Percentage of applications built with this template that pass HIPAA audits on first attempt (target: 95%+)
- **Security Incident Count:** Number of data breaches or PHI exposure incidents in applications built with template (target: 0)
- **Audit Log Completeness:** Percentage of regulatory-required events captured in audit logs (target: 100%)

### Product Quality and Performance

- **RAG Query Response Time:** P95 latency for document search + LLM response generation (target: < 3 seconds)
- **RAG Answer Accuracy:** Percentage of queries where retrieved documents are relevant to question (target: 85%+ precision)
- **System Uptime:** Availability of deployed applications (target: 99.9%+ uptime)

### User Satisfaction

- **Developer Net Promoter Score:** How likely developers are to recommend template to colleagues (target: NPS > 50)
- **Setup Friction Score:** Number of blockers/issues encountered during initial setup (target: < 3 issues requiring support)
- **Documentation Clarity Rating:** Developer rating of setup guides and security documentation (target: 4.5/5 stars)

### Business Impact

- **Cost Reduction:** Estimated dollar value saved by using template vs. building compliance infrastructure from scratch (target: $200K+ savings per team)
- **Compliance Cost Reduction:** Reduction in audit preparation time and consultant fees (target: 50% reduction)
- **Time to Market:** Reduction in months from project start to compliant production deployment (target: 6-9 months saved)
