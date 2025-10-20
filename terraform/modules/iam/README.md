# IAM Module

## Purpose

Provision IAM roles and policies with strict least-privilege access for the backend application to interact with AWS services (S3, KMS, RDS, Bedrock) in a HIPAA-compliant manner.

## Features

- **Backend Application Role**: IAM role for Railway-hosted FastAPI backend with AssumeRole trust policy
- **S3 Access Policy**: Least-privilege permissions for PHI documents, backups, and audit logs
- **KMS Access Policy**: Encryption/decryption operations for master key and per-tenant keys
- **Bedrock Access Policy**: AI model invocation for Anthropic Claude models
- **RDS Monitoring Role**: Optional Enhanced Monitoring role for RDS performance insights

## Security Principles

### Least Privilege

All policies use specific resource ARNs without wildcards (except where AWS APIs require it):
- S3 actions scoped to specific bucket ARNs and path prefixes
- KMS actions scoped to specific key ARNs with tag-based conditions
- Bedrock actions scoped to Anthropic Claude model family only

### Resource Isolation

- Documents: Limited to `tenants/*` prefix for multi-tenant isolation
- Backups: Write-only access to prevent tampering
- Audit Logs: Append-only access for compliance trail integrity
- Tenant Keys: Tag-based conditions ensure only application-managed keys are accessible

## Usage Example

```hcl
module "iam" {
  source = "./modules/iam"

  environment = "production"

  s3_bucket_documents_arn   = module.s3.s3_bucket_documents_arn
  s3_bucket_backups_arn     = module.s3.s3_bucket_backups_arn
  s3_bucket_audit_logs_arn  = module.s3.s3_bucket_audit_logs_arn

  kms_master_key_arn        = module.kms.kms_master_key_arn

  rds_arn                   = module.rds.rds_arn

  external_id               = var.railway_external_id
  enable_rds_monitoring     = true

  tags = {
    Project     = "HIPAA-Compliant Stack"
    CostCenter  = "Engineering"
  }
}
```

## Railway Integration

### AssumeRole Setup

The backend application role uses an AssumeRole trust policy with an external ID for security:

1. **In Railway**: Configure AWS credentials with permissions to assume the backend role:
   ```bash
   AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
   AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   AWS_REGION=us-east-1
   APP_IAM_ROLE_ARN=arn:aws:iam::123456789012:role/hipaa-app-backend-production
   EXTERNAL_ID=railway-hipaa-app
   ```

2. **In Application Code**: Use boto3 STS to assume the role:
   ```python
   import boto3

   sts_client = boto3.client('sts')
   assumed_role = sts_client.assume_role(
       RoleArn=os.getenv('APP_IAM_ROLE_ARN'),
       RoleSessionName='railway-backend-session',
       ExternalId=os.getenv('EXTERNAL_ID')
   )

   credentials = assumed_role['Credentials']
   s3_client = boto3.client(
       's3',
       aws_access_key_id=credentials['AccessKeyId'],
       aws_secret_access_key=credentials['SecretAccessKey'],
       aws_session_token=credentials['SessionToken']
   )
   ```

### Alternative: OIDC Integration

For enhanced security without long-lived credentials, use OIDC-based federation (future enhancement):
- Configure Railway as OIDC identity provider in AWS
- Update trust policy to use OIDC principal instead of root account
- No access keys needed in Railway environment

## Policy Scopes

### S3 Access Policy

**Actions Allowed:**
- `s3:ListBucket` - List contents of documents, backups, audit logs buckets
- `s3:GetObject` - Read documents from tenants prefix
- `s3:PutObject` - Write documents to tenants prefix, write backups, append audit logs
- `s3:DeleteObject` - Delete documents from tenants prefix

**Resource Restrictions:**
- Documents: Scoped to `${bucket_arn}/tenants/*` for multi-tenant isolation
- Backups: Write-only access to prevent unauthorized reads
- Audit Logs: Restricted to `application-logs/` prefix

### KMS Access Policy

**Actions Allowed:**
- `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey` - Encryption operations
- `kms:CreateKey` - Create per-tenant KMS keys at runtime
- `kms:EnableKeyRotation` - Enable automatic key rotation for tenant keys
- `kms:DescribeKey`, `kms:ListKeys` - Key metadata operations

**Resource Restrictions:**
- Master Key: Specific ARN for infrastructure encryption
- Tenant Keys: Tag-based conditions (`Environment=production`, `ManagedBy=Application`)
- Region Lock: CreateKey restricted to current AWS region

**Wildcard Usage:**
- `Resource: "*"` used only for `kms:CreateKey` and `kms:ListKeys` (AWS API requirement)
- All other actions use specific ARNs or tag-based conditions

### Bedrock Access Policy

**Actions Allowed:**
- `bedrock:InvokeModel` - Invoke foundation models for AI capabilities

**Resource Restrictions:**
- Model Family: `anthropic.claude-*` only (no other model families)
- Region: Current AWS region only

### RDS Enhanced Monitoring Role

**Managed Policy:**
- `AmazonRDSEnhancedMonitoringRole` - AWS-managed policy for RDS metrics publishing

**Conditional Creation:**
- Only created when `enable_rds_monitoring = true`
- Used by RDS module for Performance Insights and Enhanced Monitoring

## Input Variables

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `environment` | string | Yes | - | Environment name (dev, staging, production) |
| `s3_bucket_documents_arn` | string | Yes | - | ARN of documents S3 bucket |
| `s3_bucket_backups_arn` | string | Yes | - | ARN of backups S3 bucket |
| `s3_bucket_audit_logs_arn` | string | Yes | - | ARN of audit logs S3 bucket |
| `kms_master_key_arn` | string | Yes | - | ARN of KMS master key |
| `rds_arn` | string | No | "" | ARN of RDS instance |
| `external_id` | string | No | "railway-hipaa-app" | External ID for AssumeRole trust policy |
| `enable_rds_monitoring` | bool | No | false | Enable RDS Enhanced Monitoring role |
| `tags` | map(string) | No | {} | Additional resource tags |

## Output Values

| Output | Description |
|--------|-------------|
| `app_iam_role_arn` | ARN of the backend application IAM role |
| `app_iam_role_name` | Name of the backend application IAM role |
| `rds_monitoring_role_arn` | ARN of the RDS monitoring role (if enabled) |
| `s3_policy_arn` | ARN of the S3 access policy |
| `kms_policy_arn` | ARN of the KMS access policy |
| `bedrock_policy_arn` | ARN of the Bedrock access policy |

## Dependencies

**Required Modules:**
- `modules/s3` - Provides S3 bucket ARNs
- `modules/kms` - Provides KMS master key ARN
- `modules/rds` - Provides RDS instance ARN (optional)

**Dependency Order:**
1. Deploy KMS module
2. Deploy S3 module
3. Deploy RDS module (optional)
4. Deploy IAM module (depends on outputs from above)

## HIPAA Compliance

### Administrative Safeguards (164.308)

- **Access Management**: Role-based access with least-privilege policies
- **Workforce Security**: External ID prevents unauthorized role assumption
- **Audit Controls**: CloudTrail logs all IAM actions

### Technical Safeguards (164.312)

- **Access Control**: Tag-based conditions for tenant key isolation
- **Encryption**: KMS policies enforce encryption for all data operations
- **Audit Logging**: S3 policy enforces append-only audit log writes

## Testing

Run unit tests for the IAM module:

```bash
cd terraform/tests
go test -v ./unit/iam_test.go -timeout 10m
```

Tests verify:
- IAM role creation with correct trust policy
- Policy attachments to role
- No wildcard actions in policies (least privilege)
- Tag-based conditions for tenant key access
- RDS monitoring role creation (conditional)

## Troubleshooting

### AssumeRole Access Denied

**Error**: `User is not authorized to perform: sts:AssumeRole`

**Solution**: Verify Railway AWS credentials have `sts:AssumeRole` permission for the backend role ARN.

### S3 Access Denied

**Error**: `Access Denied` when accessing S3 buckets

**Solution**:
1. Verify role has assumed successfully
2. Check S3 bucket ARNs match module inputs
3. Verify documents are under `tenants/` prefix

### KMS Access Denied for Tenant Keys

**Error**: `KMS key is not authorized for use`

**Solution**:
1. Verify tenant keys have tags: `Environment={environment}`, `ManagedBy=Application`
2. Ensure keys are in the same AWS region
3. Check KMS key policy allows IAM role access

## Future Enhancements

- **OIDC Integration**: Replace access keys with OIDC-based federation
- **Session Tags**: Use session tags for finer-grained tenant isolation
- **Service Control Policies**: Organization-level SCPs for additional guardrails
- **AWS Secrets Manager**: Policy for retrieving RDS credentials and OIDC secrets

## References

- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [IAM Policy Reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies.html)
- [AssumeRole with External ID](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-user_externalid.html)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
