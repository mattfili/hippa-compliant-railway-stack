# HIPAA Compliance Mapping - AWS Infrastructure

Comprehensive mapping of HIPAA Security Rule requirements to AWS infrastructure controls implemented via Terraform.

## Table of Contents

1. [Overview](#overview)
2. [Administrative Safeguards](#administrative-safeguards)
3. [Physical Safeguards](#physical-safeguards)
4. [Technical Safeguards](#technical-safeguards)
5. [Compliance Checklist](#compliance-checklist)
6. [Continuous Monitoring](#continuous-monitoring)
7. [Audit and Accountability](#audit-and-accountability)
8. [Risk Assessment](#risk-assessment)

## Overview

This document maps HIPAA Security Rule requirements (45 CFR Parts 160, 162, and 164) to the AWS infrastructure components provisioned by Terraform for the HIPAA-compliant multi-tenant document management system.

###

 Scope of PHI Protection

**Protected Health Information (PHI) Boundaries:**
- **PHI Storage:** RDS PostgreSQL (encrypted at rest), S3 buckets (encrypted at rest)
- **PHI Transit:** TLS 1.2+ for all connections (Railway→RDS, Application→S3, User→Application)
- **PHI Processing:** Railway-hosted FastAPI backend (stateless, no PHI cached beyond request lifecycle)

**Non-PHI Components:**
- VPC, subnets, security groups (infrastructure metadata)
- IAM roles and policies (access control configurations)
- CloudTrail, AWS Config logs (audit metadata)
- Terraform state (infrastructure configuration, contains resource IDs but no PHI)

## Administrative Safeguards

### 164.308(a)(1)(i) - Security Management Process

#### Risk Analysis (Required)

**Control:** Infrastructure as Code (Terraform) enables version-controlled, auditable risk assessment.

**Implementation:**
- All infrastructure defined in Terraform modules with explicit security configurations
- Code reviews required for infrastructure changes (GitHub pull requests)
- Automated static analysis with `tflint` to detect security misconfigurations
- Regular `terraform plan` execution to detect drift from expected state

**Evidence:**
- Terraform state files showing current infrastructure configuration
- Git commit history showing infrastructure changes over time
- tflint configuration in `.tflint.hcl` enforcing security rules
- CI/CD pipeline logs showing validation checks

**Terraform Resources:**
- All modules in `terraform/modules/`
- CI/CD pipeline: `.github/workflows/terraform-ci.yml`

---

#### Risk Management (Required)

**Control:** AWS Config rules for continuous compliance monitoring and alerting.

**Implementation:**
- 6+ managed Config rules monitoring HIPAA-relevant misconfigurations:
  - `s3-bucket-server-side-encryption-enabled`
  - `rds-storage-encrypted`
  - `rds-instance-public-access-check`
  - `iam-policy-no-statements-with-admin-access`
  - `cloudtrail-enabled`
  - `vpc-sg-open-only-to-authorized-ports`
- SNS topic for real-time alerts on non-compliance
- Manual remediation process (auto-remediation disabled for safety)

**Evidence:**
- AWS Config dashboard showing active rules and compliance status
- SNS topic subscriptions for alert notifications
- CloudWatch logs showing Config rule evaluations

**Terraform Resources:**
- `modules/config/main.tf` - Config recorder, rules, SNS topic
- `modules/config/outputs.tf` - Config recorder name, SNS topic ARN

---

#### Sanction Policy (Required)

**Control:** Access controls and audit logging enable enforcement of sanction policies.

**Implementation:**
- IAM policies restrict unauthorized access to PHI
- CloudTrail logs all API calls for audit and investigation
- Application audit logs record user actions on PHI
- Immutable audit logs in S3 with versioning prevent tampering

**Evidence:**
- IAM policy documents showing least-privilege access
- CloudTrail logs in S3 audit bucket
- Application `audit_logs` table in RDS

**Terraform Resources:**
- `modules/iam/main.tf` - IAM roles and policies
- `modules/s3/main.tf` - Audit logs bucket with versioning
- Application code: `backend/app/models/audit_log.py`

---

#### Information System Activity Review (Required)

**Control:** CloudTrail and AWS Config provide centralized logging for review.

**Implementation:**
- CloudTrail logs all AWS API calls to S3 audit bucket
- AWS Config tracks resource configuration changes over time
- Application audit logs record PHI access and modifications
- Logs aggregated in S3 for analysis and reporting

**Evidence:**
- CloudTrail trail configuration
- AWS Config delivery channel to S3
- S3 audit bucket with log aggregation

**Terraform Resources:**
- `modules/s3/main.tf` - Audit logs bucket
- `modules/config/main.tf` - Config delivery channel
- Optional: CloudTrail configuration (manual or separate module)

---

### 164.308(a)(3)(i) - Workforce Security

#### Authorization and/or Supervision (Required)

**Control:** IAM roles and policies enforce least-privilege access.

**Implementation:**
- Backend application IAM role with specific resource ARNs (no wildcards)
- Policies grant only necessary permissions: S3 (read/write specific buckets), KMS (encrypt/decrypt), RDS (connect), Bedrock (invoke models)
- No IAM users with static credentials; use IAM roles for temporary credentials
- Terraform admin user separate from application roles

**Evidence:**
- IAM policy documents in Terraform code
- AWS IAM console showing role trust policies and permissions
- No overly permissive policies (detected by Config rule)

**Terraform Resources:**
- `modules/iam/main.tf` - Backend application role and policies
- `modules/iam/outputs.tf` - Role ARN for Railway integration

---

### 164.308(a)(4)(i) - Information Access Management

#### Access Authorization (Required)

**Control:** Multi-tenant Row-Level Security (RLS) and IAM policies.

**Implementation:**
- **AWS Infrastructure Level:** IAM policies restrict access to S3 buckets and RDS instances
- **Application Level:** RLS policies in PostgreSQL ensure tenants only access their own data
- **Per-Tenant Encryption:** Each tenant has dedicated KMS key for data encryption
- **OIDC Authentication:** Backend enforces authentication before allowing API access

**Evidence:**
- IAM policy statements showing resource-specific permissions
- PostgreSQL RLS policies on `documents` table (application-level)
- Per-tenant KMS keys in `tenants.kms_key_arn` column
- OIDC configuration in Railway environment variables

**Terraform Resources:**
- `modules/iam/main.tf` - IAM access policies
- `modules/kms/main.tf` - Master KMS key (per-tenant keys created by application)
- Application code: `backend/app/models/tenant.py`, RLS migrations

---

### 164.308(a)(5)(i) - Security Awareness and Training

**Control:** Documentation and runbooks for infrastructure operations.

**Implementation:**
- Comprehensive deployment guides and troubleshooting documentation
- Operations runbooks for common tasks
- README files for each Terraform module
- Disaster recovery procedures documented

**Evidence:**
- Documentation in `docs/` directory
- Module READMEs in `terraform/modules/*/README.md`
- Training materials for DevOps team

**Terraform Resources:**
- All documentation files in `docs/` and `terraform/README.md`

---

### 164.308(a)(7)(i) - Contingency Plan

#### Data Backup Plan (Required)

**Control:** Automated RDS backups and S3 versioning.

**Implementation:**
- **RDS Automated Backups:** Daily snapshots with 30-day retention
- **RDS Manual Snapshots:** Created before destructive operations
- **S3 Versioning:** All buckets have versioning enabled
- **S3 Lifecycle Policies:** Transition to Glacier for long-term retention (7 years - HIPAA requirement)
- **Terraform State Backups:** State versioned in S3 for infrastructure rollback

**Evidence:**
- RDS backup retention period in Terraform configuration
- S3 versioning configuration in Terraform code
- S3 lifecycle policies transitioning to Glacier
- S3 state bucket version history

**Terraform Resources:**
- `modules/rds/main.tf` - Backup retention configuration
- `modules/s3/main.tf` - Versioning and lifecycle policies
- `backend.tf` - State backend with versioning

---

#### Disaster Recovery Plan (Required)

**Control:** Multi-AZ deployments and documented recovery procedures.

**Implementation:**
- **RDS Multi-AZ:** Automatic failover to standby in different AZ (staging/production)
- **Read Replicas:** Additional redundancy for production environment
- **S3 Cross-Region Replication (Future):** Planned for cross-region disaster recovery
- **Point-in-Time Recovery:** RDS PITR enabled with 5-minute granularity
- **Recovery Runbook:** Documented procedures for RDS and S3 recovery

**Evidence:**
- Terraform configuration showing Multi-AZ enabled
- RDS PITR logs and backup windows
- Disaster recovery documentation in `docs/TERRAFORM_DISASTER_RECOVERY.md`

**Terraform Resources:**
- `modules/rds/main.tf` - Multi-AZ and read replica configuration
- `docs/TERRAFORM_DISASTER_RECOVERY.md` - Recovery procedures

---

#### Emergency Mode Operation Plan (Addressable)

**Control:** Read-only mode and manual fail-over procedures.

**Implementation:**
- **RDS Read Replica:** Can be promoted to primary in emergency
- **Application Read-Only Mode:** Backend supports read-only flag to prevent writes
- **Manual Failover:** Documented steps for promoting read replica
- **Backup Restoration:** Documented steps for restoring from snapshot

**Evidence:**
- Read replica configuration in Terraform
- Application code supporting read-only mode
- Failover procedures in disaster recovery documentation

**Terraform Resources:**
- `modules/rds/main.tf` - Read replica resource (conditional)
- Application code: `backend/app/config.py` - Read-only configuration
- `docs/TERRAFORM_DISASTER_RECOVERY.md` - Emergency procedures

---

### 164.308(a)(8) - Evaluation

**Control:** Regular compliance audits and Config rule monitoring.

**Implementation:**
- **Automated Compliance Checks:** AWS Config rules evaluate HIPAA-relevant configurations daily
- **Manual Security Reviews:** Periodic audits of IAM policies, security groups, encryption status
- **Penetration Testing:** Scheduled security assessments of application and infrastructure
- **Compliance Reporting:** Config compliance dashboard and SNS alerts

**Evidence:**
- AWS Config compliance timeline
- Config rule evaluation history
- Manual audit reports (performed by security team)
- Penetration test results (external audit)

**Terraform Resources:**
- `modules/config/main.tf` - Config rules for continuous evaluation

---

## Physical Safeguards

### 164.310(a)(1) - Facility Access Controls

**Control:** AWS-managed physical security (SOC 2, HITRUST, ISO 27001 certified).

**Implementation:**
- **Data Center Security:** AWS data centers have physical access controls, surveillance, environmental controls
- **Multi-AZ Deployment:** PHI stored across multiple physically separate availability zones
- **Geographic Isolation:** Each AZ in separate flood plain with independent power and network
- **AWS Compliance Certifications:** AWS maintains HIPAA-eligible services and BAA

**Evidence:**
- AWS SOC 2 Type II report
- AWS HITRUST certification
- AWS BAA (Business Associate Agreement) signed
- Terraform configuration showing Multi-AZ deployment

**Terraform Resources:**
- `modules/rds/main.tf` - Multi-AZ configuration
- `modules/vpc/main.tf` - Subnets across 3 AZs

---

### 164.310(b) - Workstation Use

**Control:** No workstations store PHI; Railway infrastructure is stateless.

**Implementation:**
- **No PHI on Railway:** Railway hosts stateless compute (FastAPI backend); no PHI cached in memory beyond request lifecycle
- **No PHI on Developer Workstations:** Developers use sanitized test data; production data never downloaded
- **Encryption in Transit:** All PHI access via HTTPS with TLS 1.2+
- **Session Management:** Short-lived JWT tokens for API access

**Evidence:**
- Application architecture documentation showing stateless design
- Developer guidelines prohibiting production data access
- HTTPS/TLS enforcement in Railway and application code

**Terraform Resources:**
- Infrastructure provisions AWS resources only; Railway configuration in `railway.json`

---

### 164.310(c) - Workstation Security

**Control:** Access controls and encryption for workstation connections.

**Implementation:**
- **Encrypted Connections:** All access to AWS resources via HTTPS/TLS 1.2+
- **VPN/Bastion (Future):** Direct RDS access requires VPN or bastion host (RDS in private subnet)
- **IAM Access Keys:** Workstation access uses IAM credentials with MFA (recommended)
- **Railway Access Controls:** Railway project access restricted to authorized team members

**Evidence:**
- RDS configuration showing no public accessibility
- Security group rules allowing only private subnet access
- IAM user/role configurations with MFA enforcement

**Terraform Resources:**
- `modules/rds/main.tf` - `publicly_accessible = false`
- `modules/networking/main.tf` - Security groups with private access only

---

### 164.310(d)(1) - Device and Media Controls

#### Disposal (Required)

**Control:** Secure deletion and AWS-managed media destruction.

**Implementation:**
- **RDS Deletion Protection:** Production databases have deletion protection enabled
- **Final Snapshots:** Manual snapshots created before RDS termination
- **S3 Object Deletion:** Versioning prevents permanent deletion; objects recoverable
- **AWS Media Destruction:** AWS securely destroys storage media per NIST 800-88 guidelines
- **Terraform Destroy Safeguards:** Production resources require explicit approval before destruction

**Evidence:**
- RDS deletion protection configuration in Terraform
- S3 versioning and lifecycle policies
- AWS media destruction certification in SOC 2 report

**Terraform Resources:**
- `modules/rds/main.tf` - `deletion_protection = true` for production
- `modules/s3/main.tf` - S3 versioning and lifecycle expiration

---

#### Media Re-use (Required)

**Control:** KMS encryption prevents data recovery from re-used storage.

**Implementation:**
- **KMS Encryption:** All RDS and S3 storage encrypted with KMS; data unrecoverable without key access
- **Key Rotation:** KMS keys rotate annually; old key material still decrypts existing data
- **Secure Snapshots:** RDS snapshots encrypted with same KMS key
- **AWS Storage Sanitization:** AWS sanitizes storage before re-allocation

**Evidence:**
- KMS key configuration with rotation enabled
- RDS and S3 encryption configuration
- AWS storage sanitization policies in compliance documentation

**Terraform Resources:**
- `modules/kms/main.tf` - Key rotation enabled
- `modules/rds/main.tf`, `modules/s3/main.tf` - Encryption configuration

---

## Technical Safeguards

### 164.312(a)(1) - Access Control

#### Unique User Identification (Required)

**Control:** OIDC authentication with unique user identifiers.

**Implementation:**
- **OIDC Integration:** Backend authenticates users via OIDC provider (Cognito, Auth0)
- **Unique User IDs:** Each user has unique ID in `users` table
- **IAM Roles:** Backend application uses IAM role (no shared credentials)
- **Audit Logging:** All PHI access logged with user ID and timestamp

**Evidence:**
- OIDC configuration in Railway environment variables
- `users` table schema showing unique `id` column
- IAM role trust policies in Terraform code
- Audit logs with user ID and action

**Terraform Resources:**
- `modules/iam/main.tf` - IAM role for backend application
- Application code: `backend/app/auth/oidc.py`, `backend/app/models/user.py`

---

#### Emergency Access Procedure (Required)

**Control:** Break-glass IAM user for emergency access.

**Implementation:**
- **Emergency Admin User:** IAM user with MFA for emergency RDS access
- **IAM Database Authentication:** Emergency access uses IAM credentials (temporary)
- **Read-Only Emergency Mode:** Application supports read-only mode to prevent writes during incident
- **Audit Trail:** All emergency access logged in CloudTrail

**Evidence:**
- Emergency admin IAM user configuration (manual, not in Terraform)
- RDS IAM authentication enabled
- CloudTrail logs showing emergency access events

**Terraform Resources:**
- `modules/rds/main.tf` - `iam_database_authentication_enabled = true`

---

#### Automatic Logoff (Addressable)

**Control:** JWT token expiration and session timeouts.

**Implementation:**
- **JWT Token Expiration:** Access tokens expire after 1 hour (configurable)
- **Refresh Token Expiration:** Refresh tokens expire after 7 days
- **Application Session Timeout:** Backend enforces token expiration (no automatic renewal)
- **Railway Session Timeout:** Railway console sessions timeout after inactivity

**Evidence:**
- JWT configuration in application code
- Token expiration logs in application audit logs

**Terraform Resources:**
- Application code: `backend/app/auth/jwt.py` - Token expiration configuration

---

#### Encryption and Decryption (Addressable)

**Control:** KMS encryption for data at rest and TLS for data in transit.

**Implementation:**
- **RDS Encryption at Rest:** All RDS instances encrypted with KMS master key
- **S3 Encryption at Rest:** All S3 buckets use SSE-KMS encryption
- **Per-Tenant Encryption:** Each tenant has dedicated KMS key for additional isolation
- **TLS 1.2+ in Transit:** All connections use TLS 1.2 or higher (RDS, S3, Railway, API)
- **Certificate Validation:** Application validates TLS certificates

**Evidence:**
- RDS encryption configuration in Terraform
- S3 SSE-KMS configuration in Terraform
- Per-tenant KMS key ARNs in `tenants` table
- TLS configuration in application and Railway

**Terraform Resources:**
- `modules/kms/main.tf` - Master KMS key
- `modules/rds/main.tf` - `storage_encrypted = true`, `kms_key_id` reference
- `modules/s3/main.tf` - SSE-KMS configuration
- Application code: Per-tenant key creation in `backend/app/services/tenant_service.py`

---

### 164.312(b) - Audit Controls

**Control:** CloudTrail, AWS Config, and application audit logs.

**Implementation:**
- **CloudTrail Logging:** All AWS API calls logged to S3 audit bucket with immutability
- **AWS Config Logging:** Resource configuration changes tracked over time
- **Application Audit Logs:** User actions on PHI logged to `audit_logs` table and exported to S3
- **Log Retention:** Audit logs retained for 7 years (HIPAA requirement)
- **Log Integrity:** S3 versioning and MFA Delete prevent tampering

**Evidence:**
- CloudTrail configuration and S3 delivery
- AWS Config delivery channel to S3
- Application audit log schema and export jobs
- S3 lifecycle policies with 7-year retention

**Terraform Resources:**
- `modules/s3/main.tf` - Audit logs bucket with versioning and lifecycle
- `modules/config/main.tf` - Config delivery channel
- Application code: `backend/app/models/audit_log.py`, audit log middleware

---

### 164.312(c)(1) - Integrity

**Control:** S3 versioning, RDS backups, and data validation.

**Implementation:**
- **S3 Versioning:** All S3 buckets have versioning; deleted/modified objects recoverable
- **S3 Object Lock (Optional):** Audit logs bucket can use object lock for immutability
- **RDS Automated Backups:** Daily snapshots with 30-day retention prevent data loss
- **Application-Level Validation:** Backend validates data integrity before storage
- **Checksums:** S3 and RDS use checksums to detect corruption

**Evidence:**
- S3 versioning configuration in Terraform
- RDS backup configuration in Terraform
- Application validation logic in code
- S3 and RDS integrity checks in AWS documentation

**Terraform Resources:**
- `modules/s3/main.tf` - Versioning enabled on all buckets
- `modules/rds/main.tf` - Automated backup configuration

---

### 164.312(d) - Person or Entity Authentication

**Control:** OIDC authentication and IAM role-based access.

**Implementation:**
- **User Authentication:** OIDC provider (Cognito, Auth0) authenticates end users
- **API Authentication:** JWT tokens validate user identity for API access
- **Application Authentication:** Backend uses IAM role to authenticate to AWS services
- **MFA Support:** OIDC provider supports multi-factor authentication

**Evidence:**
- OIDC configuration in Railway environment variables
- JWT token validation in application middleware
- IAM role trust policies in Terraform

**Terraform Resources:**
- `modules/iam/main.tf` - IAM role for backend application
- Application code: `backend/app/auth/oidc.py`, `backend/app/auth/jwt.py`

---

### 164.312(e)(1) - Transmission Security

#### Integrity Controls (Addressable)

**Control:** TLS 1.2+ for all network connections.

**Implementation:**
- **RDS TLS Connections:** PostgreSQL configured to require TLS 1.2+
- **S3 TLS Connections:** S3 API accessed via HTTPS only
- **API TLS Connections:** Railway enforces HTTPS for all API traffic
- **VPC Endpoints:** S3 and RDS accessed via VPC endpoints (no public internet)

**Evidence:**
- RDS parameter group configuration (future enhancement to enforce TLS)
- S3 bucket policies requiring HTTPS
- Railway HTTPS enforcement
- VPC endpoint configuration in Terraform

**Terraform Resources:**
- `modules/vpc/main.tf` - VPC endpoints for S3, RDS, Bedrock
- `modules/s3/main.tf` - Bucket policies requiring HTTPS (future enhancement)

---

#### Encryption (Addressable)

**Control:** TLS 1.2+ encryption for data in transit.

**Implementation:**
- **TLS 1.2+ Everywhere:** All connections use TLS 1.2 or higher
- **Railway HTTPS:** Railway automatically provisions TLS certificates
- **AWS Service Encryption:** RDS, S3, and Bedrock connections encrypted with TLS
- **Certificate Validation:** Application validates TLS certificates

**Evidence:**
- Railway HTTPS configuration
- AWS service TLS configuration
- Application TLS validation code

**Terraform Resources:**
- Infrastructure provisions private connectivity; TLS enforced by AWS services and Railway

---

## Compliance Checklist

### Infrastructure Security Checklist

- [ ] **RDS has no public IP address:** `publicly_accessible = false`
  - Verify: `terraform output rds_endpoint` should show private IP
  - AWS Console: RDS > Databases > Check "Publicly accessible" is No

- [ ] **All S3 buckets block public access:** `aws_s3_bucket_public_access_block`
  - Verify: `aws s3api get-public-access-block --bucket <bucket-name>`
  - All settings should be `true`

- [ ] **All S3 buckets use SSE-KMS encryption:** `aws_s3_bucket_server_side_encryption_configuration`
  - Verify: `aws s3api get-bucket-encryption --bucket <bucket-name>`
  - Should show `SSE-KMS` with KMS key ARN

- [ ] **KMS key rotation enabled:** `enable_key_rotation = true`
  - Verify: `aws kms get-key-rotation-status --key-id <key-id>`
  - Should show `KeyRotationEnabled: true`

- [ ] **Security groups deny unrestricted inbound:** No `0.0.0.0/0` on sensitive ports
  - Verify: `aws ec2 describe-security-groups --group-ids <sg-id>`
  - Review ingress rules for overly permissive entries

- [ ] **IAM policies use specific resource ARNs:** No wildcard `*` resources
  - Verify: Review IAM policy JSON documents
  - Check for `"Resource": "*"` statements

- [ ] **CloudTrail logging enabled:** (Manual setup or separate module)
  - Verify: `aws cloudtrail describe-trails`
  - At least one trail should be logging

- [ ] **AWS Config recording enabled:** `aws_config_configuration_recorder_status`
  - Verify: `aws configservice describe-configuration-recorder-status`
  - Should show `recording: true`

- [ ] **RDS automated backups enabled:** `backup_retention_period = 30`
  - Verify: `aws rds describe-db-instances --query 'DBInstances[*].[DBInstanceIdentifier,BackupRetentionPeriod]'`
  - Should show 30 days for production

- [ ] **S3 versioning enabled on all buckets:** `aws_s3_bucket_versioning`
  - Verify: `aws s3api get-bucket-versioning --bucket <bucket-name>`
  - Should show `Status: Enabled`

- [ ] **VPC endpoints used for S3/RDS access:** `aws_vpc_endpoint`
  - Verify: `terraform output vpc_endpoint_s3_id` and `vpc_endpoint_rds_id`
  - Endpoints should be in "available" state

- [ ] **TLS 1.2+ enforced for RDS connections:** (Check application configuration)
  - Verify: Application connection string includes `sslmode=require`
  - Future: RDS parameter group enforces TLS

### Operational Security Checklist

- [ ] **Terraform state encrypted and versioned:** S3 backend with versioning
- [ ] **Manual RDS snapshots before destructive changes:** Document in runbook
- [ ] **Per-tenant KMS keys created on tenant provisioning:** Application logic
- [ ] **Audit logs exported to S3 daily:** Application export job
- [ ] **Config rules monitored and alerts configured:** SNS subscriptions active
- [ ] **IAM users have MFA enabled:** Manual verification in IAM console
- [ ] **Railway environment variables secured:** No secrets in version control
- [ ] **Deletion protection enabled for production RDS:** `deletion_protection = true`
- [ ] **Read replicas deployed for production:** `enable_read_replica = true`
- [ ] **Multi-AZ enabled for staging and production:** `multi_az = true`

## Continuous Monitoring

### AWS Config Rules

The following Config rules continuously monitor compliance:

| Rule | HIPAA Requirement | Compliance Check |
|------|-------------------|------------------|
| `s3-bucket-server-side-encryption-enabled` | 164.312(a)(2)(iv) | Encryption at rest |
| `rds-storage-encrypted` | 164.312(a)(2)(iv) | Encryption at rest |
| `rds-instance-public-access-check` | 164.312(a)(1) | Access control |
| `iam-policy-no-statements-with-admin-access` | 164.308(a)(3)(i) | Least privilege |
| `cloudtrail-enabled` | 164.312(b) | Audit logging |
| `vpc-sg-open-only-to-authorized-ports` | 164.312(a)(1) | Network access control |

**Config Rule Actions:**
- **Non-Compliant:** SNS alert sent to configured email/Slack
- **Remediation:** Manual review and correction (auto-remediation disabled)
- **Reporting:** Compliance timeline available in AWS Config dashboard

### CloudTrail Monitoring

CloudTrail logs the following HIPAA-relevant events:
- **IAM Changes:** User/role creation, policy modifications, access key usage
- **KMS Operations:** Key usage, key rotation, policy changes
- **RDS Operations:** Instance modifications, snapshot creation/restoration
- **S3 Operations:** Bucket policy changes, object access (if configured)
- **Config Operations:** Rule creation, recorder status changes

**CloudTrail Configuration:**
- **Log Delivery:** S3 audit bucket with immutability (versioning + MFA Delete)
- **Log Retention:** 7 years (via S3 lifecycle policy)
- **Log Integrity:** Log file validation enabled

### Application Audit Logs

The backend application logs the following PHI access events:
- **Document Access:** User ID, document ID, action (view, download), timestamp, tenant ID
- **Document Upload:** User ID, document metadata, encryption key used, timestamp
- **Document Deletion:** User ID, document ID, soft-delete flag, timestamp
- **Tenant Management:** User ID, tenant changes, timestamp

**Audit Log Storage:**
- **Primary:** PostgreSQL `audit_logs` table
- **Secondary:** Exported to S3 audit bucket daily
- **Retention:** 7 years (HIPAA requirement)

## Audit and Accountability

### Audit Procedures

**Quarterly Security Audit:**
1. Review AWS Config compliance reports
2. Review CloudTrail logs for suspicious activity
3. Verify IAM policies still enforce least privilege
4. Check for unused IAM users/roles and deactivate
5. Verify encryption enabled on all PHI storage
6. Test disaster recovery procedures (restore from backup)

**Annual Compliance Audit:**
1. External penetration testing
2. HIPAA compliance assessment by third-party auditor
3. Review and update risk assessment documentation
4. Verify Business Associate Agreements (BAAs) current
5. Update security policies and procedures
6. Conduct workforce security awareness training

### Audit Evidence Collection

**For HIPAA Audits, Collect:**
- Terraform code showing infrastructure-as-code security controls
- AWS Config compliance reports (past 12 months)
- CloudTrail logs (past 12 months or as requested)
- Application audit logs (past 12 months or as requested)
- Disaster recovery test results
- Penetration test reports
- Security incident reports (if any)
- Risk assessment documentation
- Policy and procedure documents

## Risk Assessment

### Identified Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation | Residual Risk |
|------|--------|------------|------------|---------------|
| **Unauthorized PHI Access** | High | Low | IAM policies, security groups, RLS, OIDC authentication, MFA | Low |
| **Data Breach via Misconfiguration** | High | Medium | AWS Config rules, tflint, code reviews, CI/CD validation | Low-Medium |
| **Data Loss** | High | Low | RDS automated backups (30-day retention), S3 versioning, Multi-AZ | Low |
| **Ransomware Attack** | High | Low | Immutable S3 audit logs, RDS snapshots, encrypted backups | Low |
| **Insider Threat** | Medium | Low | Audit logging, least privilege IAM, CloudTrail monitoring | Low-Medium |
| **DDoS Attack** | Medium | Medium | Railway infrastructure handles scaling, AWS WAF (future) | Medium |
| **Infrastructure Failure** | Medium | Low | Multi-AZ deployment, read replicas, automated failover | Low |
| **Compliance Violation** | High | Medium | Continuous Config monitoring, SNS alerts, manual reviews | Low-Medium |

### Risk Treatment Plan

**Medium Residual Risks:**
1. **Data Breach via Misconfiguration:**
   - Action: Increase Config rule evaluation frequency
   - Action: Enable auto-remediation for critical rules (after testing)
   - Timeline: Next quarter

2. **DDoS Attack:**
   - Action: Implement AWS WAF with rate limiting
   - Action: Enable AWS Shield Standard (free tier)
   - Timeline: Next quarter

3. **Insider Threat:**
   - Action: Implement AWS GuardDuty for threat detection
   - Action: Enhance CloudTrail monitoring with automated alerts
   - Timeline: Next quarter

**Low Residual Risks:**
- Acceptable with current controls
- Continue monitoring via Config rules and CloudTrail
- Review quarterly

## Attestation

This infrastructure implementation addresses HIPAA Security Rule requirements as documented above. Continuous monitoring via AWS Config and CloudTrail ensures ongoing compliance.

**Infrastructure as Code:** All security controls are codified in Terraform and version-controlled for audit traceability.

**Compliance Status:** As of deployment, all required and addressable specifications are implemented or have documented exceptions.

**Next Review Date:** [To be scheduled quarterly]

**Responsible Party:** DevOps Team / Infrastructure Engineer

**For Audit Inquiries:** Contact security@organization.com

---

## References

- HIPAA Security Rule: 45 CFR Part 164 Subpart C
- AWS HIPAA Compliance Whitepaper: https://aws.amazon.com/compliance/hipaa-compliance/
- AWS Shared Responsibility Model: https://aws.amazon.com/compliance/shared-responsibility-model/
- NIST 800-53 Security Controls: https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final
- Terraform AWS Provider Documentation: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
