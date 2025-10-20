# AWS Infrastructure Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               Railway Platform                                   │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend (Stateless Compute)                                      │  │
│  │  - HTTPS Endpoints                                                         │  │
│  │  - JWT Authentication                                                      │  │
│  │  - No PHI Storage                                                          │  │
│  └───────────────────────────────┬──────────────────────────────────────────┘  │
└────────────────────────────────────┼────────────────────────────────────────────┘
                                     │ TLS 1.2+
                                     │ Private Connectivity
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AWS Cloud (us-east-1)                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │  VPC (10.0.0.0/16) - Multi-AZ Deployment                                   │ │
│  │                                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │ │
│  │  │ Availability Zone 1a                                                  │  │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │ │
│  │  │  │Public Subnet │  │Private Subnet│  │Private Subnet│              │  │ │
│  │  │  │10.0.1.0/24   │  │10.0.11.0/24  │  │ RDS Primary  │              │  │ │
│  │  │  │              │  │              │  │ PostgreSQL   │              │  │ │
│  │  │  │NAT Gateway 1 │  │App Resources │  │(Encrypted)   │              │  │ │
│  │  │  └──────┬───────┘  └──────────────┘  └──────────────┘              │  │ │
│  │  └─────────┼──────────────────────────────────────────────────────────┘  │ │
│  │            │                                                                │ │
│  │  ┌─────────┼──────────────────────────────────────────────────────────┐  │ │
│  │  │ Availability Zone 1b                                  │              │  │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │ │
│  │  │  │Public Subnet │  │Private Subnet│  │Private Subnet│              │  │ │
│  │  │  │10.0.2.0/24   │  │10.0.12.0/24  │  │RDS Standby   │              │  │ │
│  │  │  │              │  │              │  │(Multi-AZ)    │              │  │ │
│  │  │  │NAT Gateway 2 │  │App Resources │  │              │              │  │ │
│  │  │  └──────┬───────┘  └──────────────┘  └──────────────┘              │  │ │
│  │  └─────────┼──────────────────────────────────────────────────────────┘  │ │
│  │            │                                                                │ │
│  │  ┌─────────┼──────────────────────────────────────────────────────────┐  │ │
│  │  │ Availability Zone 1c                                  │              │  │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │ │
│  │  │  │Public Subnet │  │Private Subnet│  │Private Subnet│              │  │ │
│  │  │  │10.0.3.0/24   │  │10.0.13.0/24  │  │  RDS Read    │              │  │ │
│  │  │  │              │  │              │  │   Replica    │              │  │ │
│  │  │  │NAT Gateway 3 │  │App Resources │  │ (Production) │              │  │ │
│  │  │  └──────┬───────┘  └──────────────┘  └──────────────┘              │  │ │
│  │  └─────────┼──────────────────────────────────────────────────────────┘  │ │
│  │            │                                                                │ │
│  │  ┌─────────┴──────────┐                                                    │ │
│  │  │ Internet Gateway   │                                                    │ │
│  │  └────────────────────┘                                                    │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │  VPC Endpoints (Private Service Access)                                    │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │ │
│  │  │S3 Gateway VPC   │  │RDS Interface    │  │Bedrock Interface│           │ │
│  │  │Endpoint (Free)  │  │VPC Endpoint     │  │VPC Endpoint     │           │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘           │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │  S3 Buckets (Regional Services)                                            │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │ │
│  │  │Documents Bucket                                                       │  │ │
│  │  │- hipaa-compliant-docs-{env}-{account}                                 │  │ │
│  │  │- SSE-KMS Encryption                                                   │  │ │
│  │  │- Versioning Enabled                                                   │  │ │
│  │  │- Lifecycle: Standard → IA (90d) → Glacier (365d) → Expire (7y)       │  │ │
│  │  └─────────────────────────────────────────────────────────────────────┘  │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │ │
│  │  │Backups Bucket                                                         │  │ │
│  │  │- hipaa-compliant-backups-{env}-{account}                              │  │ │
│  │  │- SSE-KMS Encryption                                                   │  │ │
│  │  │- Versioning Enabled                                                   │  │ │
│  │  └─────────────────────────────────────────────────────────────────────┘  │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │ │
│  │  │Audit Logs Bucket                                                      │  │ │
│  │  │- hipaa-compliant-audit-{env}-{account}                                │  │ │
│  │  │- SSE-KMS Encryption                                                   │  │ │
│  │  │- Versioning Enabled (Immutable)                                       │  │ │
│  │  │- CloudTrail Logs, Config Snapshots, S3 Access Logs                   │  │ │
│  │  └─────────────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │  KMS (Key Management Service)                                              │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │ │
│  │  │Master KMS Key                                                         │  │ │
│  │  │- Encrypts: RDS, S3 Buckets, Terraform State                          │  │ │
│  │  │- Automatic Key Rotation Enabled (Annual)                              │  │ │
│  │  │- CloudTrail Logging for Key Usage                                     │  │ │
│  │  └─────────────────────────────────────────────────────────────────────┘  │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │ │
│  │  │Per-Tenant KMS Keys (Created by Application)                          │  │ │
│  │  │- Tenant A Key → Tenant A Documents                                    │  │ │
│  │  │- Tenant B Key → Tenant B Documents                                    │  │ │
│  │  │- Additional Data Isolation Layer                                      │  │ │
│  │  └─────────────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │  IAM (Identity and Access Management)                                      │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │ │
│  │  │Backend Application IAM Role                                           │  │ │
│  │  │- S3 Access Policy (GetObject, PutObject, DeleteObject on tenants/*)  │  │ │
│  │  │- KMS Access Policy (Encrypt, Decrypt, GenerateDataKey)               │  │ │
│  │  │- Bedrock Access Policy (InvokeModel on Claude models)                │  │ │
│  │  │- Trust Policy: Allows Railway (via AWS credentials)                  │  │ │
│  │  └─────────────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │  Security Groups (Firewall Rules)                                          │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐        │ │
│  │  │RDS Security Group│  │App Security Group│  │VPC Endpoint SG   │        │ │
│  │  │- Ingress: 5432   │  │- Ingress: 443    │  │- Ingress: 443    │        │ │
│  │  │  from App SG     │  │  from Railway IPs│  │  from App SG     │        │ │
│  │  │- Egress: None    │  │- Egress: 5432    │  │- Egress: 443     │        │ │
│  │  │  (Default deny)  │  │  to RDS SG       │  │  to Internet     │        │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘        │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │  AWS Config (Continuous Compliance Monitoring)                             │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │ │
│  │  │Config Recorder → Tracks Resource Configuration Changes               │  │ │
│  │  │Config Rules → Enforces HIPAA Compliance                               │  │ │
│  │  │  - s3-bucket-server-side-encryption-enabled                           │  │ │
│  │  │  - rds-storage-encrypted                                              │  │ │
│  │  │  - rds-instance-public-access-check                                   │  │ │
│  │  │  - iam-policy-no-statements-with-admin-access                         │  │ │
│  │  │  - cloudtrail-enabled                                                 │  │ │
│  │  │  - vpc-sg-open-only-to-authorized-ports                               │  │ │
│  │  │SNS Topic → Sends Alerts on Non-Compliance                             │  │ │
│  │  └─────────────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │  CloudTrail (Audit Logging)                                                │ │
│  │  - Logs All AWS API Calls to Audit Logs Bucket                            │ │
│  │  - Log File Validation Enabled                                             │  │
│  │  - Multi-Region Trail                                                      │  │
│  └───────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow: Document Upload

```
  User Request                Railway Backend           AWS RDS           AWS S3           AWS KMS
       │                            │                      │                │                │
       │  POST /documents           │                      │                │                │
       ├───────────────────────────>│                      │                │                │
       │                            │                      │                │                │
       │                            │  SELECT tenant_id    │                │                │
       │                            │  kms_key_arn         │                │                │
       │                            ├─────────────────────>│                │                │
       │                            │<─────────────────────┤                │                │
       │                            │  Tenant KMS Key ARN  │                │                │
       │                            │                      │                │                │
       │                            │  Encrypt document    │                │                │
       │                            │  with tenant key     │                │                │
       │                            ├───────────────────────────────────────>│                │
       │                            │                      │                │   Generate     │
       │                            │                      │                │   Data Key     │
       │                            │<───────────────────────────────────────┤                │
       │                            │  Encrypted Data Key  │                │                │
       │                            │                      │                │                │
       │                            │  Upload encrypted    │                │                │
       │                            │  document to S3      │                │                │
       │                            ├──────────────────────────────────────>│                │
       │                            │<──────────────────────────────────────┤                │
       │                            │  S3 Object URL       │                │                │
       │                            │                      │                │                │
       │                            │  INSERT INTO         │                │                │
       │                            │  documents (s3_key,  │                │                │
       │                            │  tenant_id, ...)     │                │                │
       │                            ├─────────────────────>│                │                │
       │                            │<─────────────────────┤                │                │
       │                            │  Document ID         │                │                │
       │                            │                      │                │                │
       │  {"id": "...", "status":   │                      │                │                │
       │   "uploaded"}              │                      │                │                │
       │<───────────────────────────┤                      │                │                │
```

## Security Boundaries

```
┌────────────────────────────────────────────────────────────────────────────┐
│  PHI Storage Boundary (AWS Only)                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ RDS PostgreSQL                                                        │ │
│  │ - Document metadata                                                   │ │
│  │ - Tenant information                                                  │ │
│  │ - Audit logs (who accessed what PHI)                                 │ │
│  │ - Encryption: KMS at rest, TLS 1.2+ in transit                       │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ S3 Documents Bucket                                                   │ │
│  │ - Encrypted document files (per-tenant KMS keys)                     │ │
│  │ - Versioning enables recovery                                        │ │
│  │ - Encryption: SSE-KMS at rest, TLS 1.2+ in transit                  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  Non-PHI Compute Boundary (Railway)                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ FastAPI Backend (Stateless)                                           │ │
│  │ - No PHI cached in memory beyond request lifecycle                   │ │
│  │ - PHI accessed transiently from RDS/S3, encrypted in transit         │ │
│  │ - Authentication/authorization logic                                 │ │
│  │ - API routing and business logic                                     │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
```

## Multi-Tenant Isolation

```
Tenant A                   Tenant B                   Tenant C
    │                          │                          │
    │ Tenant A KMS Key         │ Tenant B KMS Key         │ Tenant C KMS Key
    │ arn:aws:kms:...key/aaa   │ arn:aws:kms:...key/bbb   │ arn:aws:kms:...key/ccc
    │                          │                          │
    ▼                          ▼                          ▼
┌────────────────────────────────────────────────────────────────────┐
│  S3 Documents Bucket                                                │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  │ tenants/tenant-a/   │  │ tenants/tenant-b/   │  │ tenants/tenant-c/   │
│  │ - doc1.pdf (enc-A)  │  │ - report.pdf (enc-B)│  │ - file.docx (enc-C) │
│  │ - doc2.pdf (enc-A)  │  │ - data.csv (enc-B)  │  │ - image.png (enc-C) │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘
└────────────────────────────────────────────────────────────────────┘
    │                          │                          │
    │ RLS Policy               │ RLS Policy               │ RLS Policy
    │ tenant_id = 'tenant-a'   │ tenant_id = 'tenant-b'   │ tenant_id = 'tenant-c'
    │                          │                          │
    ▼                          ▼                          ▼
┌────────────────────────────────────────────────────────────────────┐
│  RDS PostgreSQL (documents table)                                  │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  │ tenant_id: tenant-a │  │ tenant_id: tenant-b │  │ tenant_id: tenant-c │
│  │ document_id: doc1   │  │ document_id: rpt1   │  │ document_id: file1  │
│  │ s3_key: .../doc1.pdf│  │ s3_key: .../rpt.pdf │  │ s3_key: .../file.docx│
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘
└────────────────────────────────────────────────────────────────────┘
```

## Legend

- **→** : Data flow direction
- **┌─┐** : Component boundary
- **[enc-A]** : Encrypted with Tenant A's KMS key
- **TLS 1.2+** : Encrypted in transit
- **SSE-KMS** : Server-side encryption with KMS
- **RLS** : Row-Level Security (PostgreSQL)

## Key Security Features

1. **Encryption at Rest:** All PHI encrypted with KMS (RDS, S3)
2. **Encryption in Transit:** TLS 1.2+ for all connections
3. **Network Isolation:** RDS in private subnets, no public IPs
4. **Multi-Tenant Isolation:** Per-tenant KMS keys + RLS policies
5. **Audit Logging:** CloudTrail, AWS Config, Application logs
6. **Access Controls:** IAM policies, Security groups, OIDC authentication
7. **High Availability:** Multi-AZ RDS, Read replicas, S3 versioning
8. **Backup & Recovery:** Automated RDS snapshots, S3 versioning, PITR
9. **Compliance Monitoring:** AWS Config rules detect misconfigurations
10. **Stateless Compute:** Railway hosts no PHI (all PHI in AWS)

## HIPAA Compliance Mapping

| HIPAA Requirement | Implementation |
|-------------------|----------------|
| **164.312(a)(2)(iv) - Encryption** | KMS for RDS/S3, TLS 1.2+ |
| **164.312(a)(1) - Access Control** | IAM, Security Groups, RLS |
| **164.312(b) - Audit Controls** | CloudTrail, Config, App Logs |
| **164.312(c)(1) - Integrity** | S3 Versioning, RDS Backups |
| **164.312(d) - Authentication** | OIDC, JWT, IAM |
| **164.312(e)(1) - Transmission Security** | TLS 1.2+, VPC Endpoints |
| **164.308(a)(7)(ii)(A) - Backup** | RDS Snapshots, S3 Versioning |

---

**For detailed information, refer to:**
- Deployment Guide: `docs/TERRAFORM_DEPLOYMENT.md`
- HIPAA Compliance Mapping: `docs/HIPAA_COMPLIANCE_MAPPING.md`
- Disaster Recovery: `docs/TERRAFORM_DISASTER_RECOVERY.md`
- Operations Runbook: `docs/TERRAFORM_OPERATIONS_RUNBOOK.md`
