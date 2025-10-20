# Railway Environment Variables Mapping

This document describes the environment variable mapping between Terraform outputs, Railway environment variables, and the application configuration.

## Overview

The application uses a two-tier environment variable strategy:

1. **User-Provided Variables**: Manually configured in Railway's dashboard
2. **Auto-Generated Variables**: Loaded from Terraform outputs during deployment

## User-Provided Environment Variables

These variables must be manually configured in Railway's dashboard before deployment:

| Railway Variable | Description | Example Value | Required |
|-----------------|-------------|---------------|----------|
| `AWS_ACCESS_KEY_ID` | AWS access key for Terraform and application | `AKIAXXXXXXXXXXXXXXXX` | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | Yes |
| `AWS_REGION` | AWS region for all resources | `us-east-1` | Yes |
| `AWS_ACCOUNT_ID` | AWS account ID for resource naming | `123456789012` | Yes |
| `ENVIRONMENT` | Deployment environment | `dev`, `staging`, or `production` | Yes |
| `RDS_PASSWORD` | RDS database master password | `SecurePassword123!` | Yes |
| `OIDC_ISSUER_URL` | OIDC provider URL | `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxx` | Yes |
| `OIDC_CLIENT_ID` | OIDC client ID | `xxxxxxxxxxxxxxxxxxxxxx` | Yes |
| `OIDC_CLIENT_SECRET` | OIDC client secret | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | Yes |
| `LOG_LEVEL` | Application logging level | `INFO`, `DEBUG`, `WARNING`, `ERROR` | No (default: INFO) |
| `ALLOWED_ORIGINS` | CORS allowed origins | `https://app.example.com,https://admin.example.com` | No |

## Auto-Generated Environment Variables

These variables are automatically loaded from Terraform outputs via `load-terraform-outputs.sh`:

| Terraform Output | Environment Variable | Config Field | Description |
|-----------------|---------------------|--------------|-------------|
| `rds_endpoint` | `RDS_ENDPOINT` | N/A (used for DATABASE_URL) | RDS primary instance endpoint (host:port) |
| `rds_reader_endpoint` | `RDS_READER_ENDPOINT` | N/A | RDS read replica endpoint (if enabled) |
| `rds_db_name` | `RDS_DB_NAME` | N/A (used for DATABASE_URL) | RDS database name |
| `rds_username` | `RDS_USERNAME` | N/A (used for DATABASE_URL) | RDS master username |
| `s3_bucket_documents` | `S3_BUCKET_DOCUMENTS` | `s3_bucket_documents` | S3 bucket for document storage |
| `s3_bucket_backups` | `S3_BUCKET_BACKUPS` | `s3_bucket_backups` | S3 bucket for backup storage |
| `s3_bucket_audit_logs` | `S3_BUCKET_AUDIT_LOGS` | `s3_bucket_audit_logs` | S3 bucket for audit log storage |
| `kms_master_key_id` | `KMS_MASTER_KEY_ID` | `kms_master_key_id` | KMS master key ID for encryption |
| `kms_master_key_arn` | `KMS_MASTER_KEY_ARN` | N/A | KMS master key ARN |
| `vpc_id` | `VPC_ID` | N/A | VPC ID for infrastructure |
| `app_iam_role_arn` | `APP_IAM_ROLE_ARN` | N/A | IAM role ARN for application |
| `aws_region` | `AWS_REGION` | `aws_region` | AWS region (overrides user-provided if different) |

## Composite Environment Variables

Some environment variables are constructed from multiple Terraform outputs:

| Variable | Construction | Example |
|----------|-------------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://${RDS_USERNAME}:${RDS_PASSWORD}@${RDS_ENDPOINT}/${RDS_DB_NAME}` | `postgresql+asyncpg://admin_user:SecurePass123!@db-prod.xxx.us-east-1.rds.amazonaws.com:5432/hipaa_db` |

## Configuration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Railway Deployment Starts                                     │
│    - User-provided env vars loaded from Railway dashboard        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Terraform Service Runs                                        │
│    - terraform init                                              │
│    - terraform workspace select $ENVIRONMENT                     │
│    - terraform apply -auto-approve                               │
│    - terraform output -json > /app/outputs.json                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Backend Service Starts                                        │
│    - startup.sh executes                                         │
│    - load-terraform-outputs.sh sources outputs.json              │
│    - Environment variables exported                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Application Initialization                                    │
│    - app/config.py loads all environment variables               │
│    - Pydantic validates configuration                            │
│    - Settings cached via @lru_cache                              │
└─────────────────────────────────────────────────────────────────┘
```

## Secrets Management

### Railway Environment Variables
Railway environment variables are encrypted at rest and in transit. However, sensitive values should follow these guidelines:

1. **AWS Credentials**: Store in Railway as environment variables (required for Terraform execution)
2. **RDS Password**: Store in Railway as environment variable (required for DATABASE_URL construction)
3. **OIDC Client Secret**: Store in Railway as environment variable

### AWS Secrets Manager (Future Enhancement)
For production deployments, consider migrating sensitive values to AWS Secrets Manager:

- OIDC client secret
- RDS password
- API keys

The application already supports AWS Secrets Manager via the `aws_secrets_manager_secret_id` configuration field.

## Setting Up Railway Environment Variables

### Step 1: Create Railway Project
1. Go to https://railway.app
2. Create new project from GitHub repository
3. Select the backend service

### Step 2: Configure Environment Variables
Navigate to the backend service settings and add the following variables:

**Required AWS Variables:**
```
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
```

**Required Environment Configuration:**
```
ENVIRONMENT=production
RDS_PASSWORD=YourSecurePassword123!
```

**Required Authentication:**
```
OIDC_ISSUER_URL=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxx
OIDC_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxx
OIDC_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Optional Configuration:**
```
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://yourdomain.com
```

### Step 3: Deploy
Push to your GitHub repository to trigger Railway deployment. Railway will:
1. Build and deploy the Terraform service first
2. Wait for Terraform to complete
3. Build and deploy the backend service (which depends on Terraform outputs)

## Troubleshooting

### Terraform Outputs Not Loading
**Symptom**: Backend service shows warning: "⚠ WARNING: Terraform outputs not found."

**Solutions**:
1. Check Terraform service logs for errors
2. Verify `/app/outputs.json` exists in Terraform container
3. Ensure backend service `dependsOn: ["terraform"]` is configured in railway.json
4. Verify ENVIRONMENT variable matches a Terraform workspace (dev/staging/production)

### Database Connection Failed
**Symptom**: Application fails to connect to RDS

**Solutions**:
1. Verify RDS_PASSWORD is set in Railway environment variables
2. Check DATABASE_URL is correctly constructed in logs
3. Verify RDS security group allows traffic from Railway IP ranges
4. Ensure RDS instance is in "available" state (check AWS Console)

### S3 Access Denied
**Symptom**: Application cannot read/write S3 buckets

**Solutions**:
1. Verify S3_BUCKET_DOCUMENTS, S3_BUCKET_BACKUPS, S3_BUCKET_AUDIT_LOGS are loaded
2. Check IAM role permissions (APP_IAM_ROLE_ARN)
3. Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY have correct permissions
4. Check S3 bucket policies and encryption settings

### KMS Encryption Errors
**Symptom**: Application fails to encrypt/decrypt data

**Solutions**:
1. Verify KMS_MASTER_KEY_ID is loaded from Terraform outputs
2. Check IAM role has kms:Encrypt, kms:Decrypt, kms:GenerateDataKey permissions
3. Verify KMS key policy allows application IAM role
4. Check AWS region matches between application and KMS key

## Environment-Specific Configuration

### Development Environment
```bash
ENVIRONMENT=dev
# Uses smaller RDS instance (db.t3.medium)
# Single-AZ deployment
# No read replica
# Lower cost infrastructure
```

### Staging Environment
```bash
ENVIRONMENT=staging
# Uses mid-tier RDS instance (db.t3.large)
# Multi-AZ deployment
# No read replica
# Production-like infrastructure
```

### Production Environment
```bash
ENVIRONMENT=production
# Uses high-performance RDS instance (db.r6g.xlarge)
# Multi-AZ deployment
# Read replica enabled
# Full HA infrastructure
# Deletion protection enabled
```

## Security Best Practices

1. **Never Commit Secrets**: Do not commit environment variables to version control
2. **Rotate Credentials**: Regularly rotate AWS access keys and RDS passwords
3. **Principle of Least Privilege**: Use IAM roles with minimal required permissions
4. **Audit Access**: Enable CloudTrail logging for all AWS API calls
5. **Encrypt in Transit**: Always use TLS 1.2+ for database and API connections
6. **Monitor Usage**: Set up CloudWatch alarms for unusual activity

## Additional Resources

- [Railway Environment Variables Documentation](https://docs.railway.app/develop/variables)
- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Terraform Output Documentation](https://www.terraform.io/docs/language/values/outputs.html)
