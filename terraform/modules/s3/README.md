# S3 Storage Module

## Purpose

This Terraform module provisions three S3 buckets for HIPAA-compliant storage:

1. **Documents Bucket** - PHI document storage with lifecycle policies
2. **Backups Bucket** - Database and application backups with Glacier transition
3. **Audit Logs Bucket** - Access logs and compliance audit trail (immutable)

All buckets are configured with SSE-KMS encryption, versioning, public access blocking, and access logging to meet HIPAA technical safeguards requirements.

## Features

- **SSE-KMS Encryption**: All buckets use AWS KMS encryption with bucket keys enabled for cost optimization
- **Versioning**: All buckets have versioning enabled for data recovery and compliance
- **Public Access Block**: All public access blocked by default (HIPAA requirement)
- **Lifecycle Policies**: Automatic transition to STANDARD_IA (90 days) and GLACIER (1 year) for cost savings
- **Access Logging**: Documents and backups buckets log access to audit bucket
- **HIPAA Retention**: 7-year retention policy (2555 days) aligned with HIPAA requirements
- **Force Destroy Protection**: All buckets protected from accidental deletion

## HIPAA 7-Year Retention Policy

The lifecycle policies implement HIPAA's minimum 7-year retention requirement for medical records:

- **Documents Bucket**:
  - 0-90 days: STANDARD storage
  - 90-365 days: STANDARD_IA (46% cost savings)
  - 365+ days: GLACIER (83% cost savings)
  - Expiration: 2555 days (7 years)

- **Backups Bucket**:
  - 0-30 days: STANDARD storage
  - 30+ days: GLACIER (long-term archival)
  - Expiration: 2555 days (7 years)

## Cost Optimization

Estimated monthly cost savings for 1TB dataset with lifecycle policies:

- **Without lifecycle**: $23/month (all STANDARD)
- **With lifecycle**: $8/month (65% reduction)
  - 3 months STANDARD_IA: $3.75
  - 9 months GLACIER: $4.00

## Usage Example

```hcl
module "s3" {
  source = "./modules/s3"

  environment             = "production"
  aws_account_id          = "123456789012"
  kms_key_id              = module.kms.kms_master_key_id
  enable_lifecycle_policies = true

  tags = {
    Project = "HIPAA Compliant Stack"
    Owner   = "DevOps Team"
  }
}
```

## Input Variables

| Variable | Type | Description | Default | Required |
|----------|------|-------------|---------|----------|
| `environment` | string | Environment name (dev, staging, production) | - | Yes |
| `aws_account_id` | string | AWS account ID for unique bucket naming | - | Yes |
| `kms_key_id` | string | KMS key ID for SSE-KMS encryption | - | Yes |
| `enable_lifecycle_policies` | bool | Enable S3 lifecycle policies for cost optimization | `true` | No |
| `documents_bucket_name` | string | Override default documents bucket name | `""` (auto-generated) | No |
| `tags` | map(string) | Additional resource tags | `{}` | No |

## Output Values

| Output | Description |
|--------|-------------|
| `s3_bucket_documents` | Documents bucket name |
| `s3_bucket_backups` | Backups bucket name |
| `s3_bucket_audit_logs` | Audit logs bucket name |
| `s3_bucket_documents_arn` | Documents bucket ARN for IAM policies |
| `s3_bucket_backups_arn` | Backups bucket ARN for IAM policies |
| `s3_bucket_audit_logs_arn` | Audit logs bucket ARN for IAM policies |
| `s3_bucket_documents_region` | Documents bucket region |

## Bucket Naming Convention

Buckets follow the pattern: `hipaa-compliant-{type}-{environment}-{account-id}`

Examples:
- `hipaa-compliant-docs-production-123456789012`
- `hipaa-compliant-backups-staging-123456789012`
- `hipaa-compliant-audit-production-123456789012`

## Access Logging

Access logs are written to the audit logs bucket with prefixes:
- Documents bucket logs → `s3://audit-bucket/documents-access/`
- Backups bucket logs → `s3://audit-bucket/backups-access/`

## Security Configuration

All buckets implement defense-in-depth security:

1. **Encryption at Rest**: SSE-KMS with customer-managed KMS key
2. **Encryption in Transit**: Enforced via bucket policies (recommended enhancement)
3. **Versioning**: Enabled for data recovery and audit trail
4. **Public Access**: Blocked at all levels (ACLs, policies, objects)
5. **Access Logging**: All access logged to centralized audit bucket
6. **Deletion Protection**: `force_destroy = false` prevents accidental deletion

## Dependencies

This module requires the following:

- **KMS Module**: Provides KMS key ID for bucket encryption
- **AWS Provider**: Version >= 5.0

## HIPAA Compliance Mapping

| HIPAA Requirement | Implementation |
|-------------------|----------------|
| 164.312(a)(2)(iv) - Encryption at Rest | SSE-KMS encryption on all buckets |
| 164.312(e)(1) - Encryption in Transit | TLS 1.2+ enforced by AWS (bucket policies recommended) |
| 164.308(a)(7)(ii)(A) - Data Backup | Versioning enabled, dedicated backups bucket |
| 164.312(b) - Audit Controls | Access logging to immutable audit bucket |
| 164.316(b)(2)(i) - Data Retention | 7-year lifecycle policy (2555 days) |

## Disaster Recovery

- **Versioning**: Recover deleted or modified objects by restoring previous versions
- **Cross-Region Replication**: Not implemented (future enhancement)
- **Backup Retention**: 7-year retention ensures long-term data availability

## Future Enhancements

- Object Lock for audit logs bucket (WORM compliance)
- S3 Inventory for bucket content auditing
- Cross-Region Replication for disaster recovery
- Bucket policies enforcing TLS 1.2+ for encryption in transit
- CloudWatch metrics and alarms for bucket access patterns
- S3 Intelligent-Tiering for automatic cost optimization

## Testing

See `/terraform/tests/unit/s3_test.go` for Terratest unit tests covering:
- Bucket creation with correct naming
- SSE-KMS encryption verification
- Versioning enabled on all buckets
- Public access blocked on all buckets
- Lifecycle policies configured correctly
- Access logging configured

## Terraform Version Requirements

- Terraform >= 1.5.0
- AWS Provider >= 5.0
