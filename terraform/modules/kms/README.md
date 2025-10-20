# KMS Module

## Purpose

Provisions an AWS KMS (Key Management Service) master key for infrastructure-level encryption with automatic key rotation and least-privilege access policies. This key serves as the master encryption key for RDS databases, S3 buckets, and other AWS services requiring encryption at rest.

## Features

- **Automatic Key Rotation**: Annual automatic key rotation enabled by default for enhanced security
- **Least-Privilege Key Policy**: Fine-grained access control with service-specific permissions
- **HIPAA Compliance**: Encryption key management aligned with HIPAA technical safeguards
- **CloudTrail Integration**: Key usage logging for audit trail requirements
- **Key Alias**: Human-readable alias for easier key reference

## Key Policy Grants

The KMS key policy implements least-privilege access with the following grants:

### Root Account Access
- **Principal**: AWS account root
- **Actions**: Full KMS permissions (required by AWS)
- **Purpose**: Administrative access and IAM policy enablement

### RDS Service Access
- **Principal**: `rds.amazonaws.com`
- **Actions**: `DescribeKey`, `CreateGrant`
- **Purpose**: Enable RDS database encryption at rest
- **Condition**: Actions only allowed via RDS service

### S3 Service Access
- **Principal**: `s3.amazonaws.com`
- **Actions**: `Decrypt`, `GenerateDataKey`
- **Purpose**: Enable S3 bucket SSE-KMS encryption

### CloudTrail Service Access
- **Principal**: `cloudtrail.amazonaws.com`
- **Actions**: `GenerateDataKey*`, `DecryptDataKey`
- **Purpose**: Enable CloudTrail log encryption
- **Condition**: Limited to CloudTrail trails in the account

## Usage Example

```hcl
module "kms" {
  source = "./modules/kms"

  environment      = "production"
  aws_account_id   = "123456789012"
  enable_key_rotation = true

  tags = {
    Project = "HIPAA Compliant Stack"
    CostCenter = "Security"
  }
}

# Reference outputs in other modules
resource "aws_db_instance" "main" {
  kms_key_id = module.kms.kms_master_key_id
  # ... other configuration
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = module.kms.kms_master_key_arn
    }
  }
}
```

## Input Variables

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `environment` | string | Yes | - | Environment name (dev, staging, production) |
| `aws_account_id` | string | Yes | - | AWS account ID (12-digit number) |
| `enable_key_rotation` | bool | No | `true` | Enable automatic annual key rotation |
| `tags` | map(string) | No | `{}` | Additional resource tags |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `kms_master_key_id` | string | KMS key ID (UUID format) for resource encryption |
| `kms_master_key_arn` | string | KMS key ARN for IAM policy configuration |
| `kms_key_alias` | string | KMS key alias name for application reference |

## Key Rotation

Automatic key rotation is enabled by default and occurs annually. Key rotation:

- **Rotation Period**: 365 days (AWS default)
- **Backward Compatibility**: Old key versions remain available for decryption
- **Transparent to Applications**: No code changes required
- **Compliance**: Meets HIPAA and industry best practices

To verify key rotation status:

```bash
aws kms get-key-rotation-status --key-id <key-id>
```

## Security Implications

### Key Deletion Protection
- **Deletion Window**: 30 days (configurable in code)
- **Purpose**: Prevents accidental key deletion
- **Recovery**: Keys scheduled for deletion can be canceled within the window

### Multi-Region Keys
- **Setting**: Disabled (single-region key)
- **Rationale**: Reduces complexity and attack surface
- **Future Enhancement**: Can be enabled for cross-region DR scenarios

### Key Policy Best Practices
- **No Wildcard Principals**: All principals explicitly defined
- **Service-Specific Conditions**: Actions restricted to specific AWS services
- **Audit Logging**: CloudTrail integration for key usage monitoring

## Dependencies

**None** - This is a foundational module with no dependencies on other infrastructure modules.

## HIPAA Compliance

This module addresses the following HIPAA requirements:

- **§164.312(a)(2)(iv)** - Encryption and Decryption: Provides encryption key management
- **§164.312(b)** - Audit Controls: CloudTrail logging of key usage
- **§164.308(a)(1)(ii)(D)** - Risk Management: Annual key rotation reduces cryptographic risk

## Troubleshooting

### Key Policy Validation Errors

If you encounter key policy validation errors during `terraform apply`:

```bash
# Validate key policy JSON syntax
terraform console
> jsonencode(jsondecode(<<EOF
{
  "Version": "2012-10-17",
  "Statement": []
}
EOF
))
```

### Permission Denied Errors

If services cannot use the key:

1. Verify service principal in key policy matches the service
2. Check condition statements aren't too restrictive
3. Ensure IAM policies grant necessary KMS permissions

### Key Rotation Not Enabled

If key rotation status shows disabled:

```bash
# Check current rotation status
aws kms get-key-rotation-status --key-id <key-id>

# Enable rotation (if disabled in Terraform)
aws kms enable-key-rotation --key-id <key-id>
```

## Cost Considerations

- **KMS Key**: $1/month per customer master key
- **API Requests**: $0.03 per 10,000 requests
- **Key Rotation**: No additional cost for automatic rotation
- **Typical Monthly Cost**: $1-5 depending on usage volume

## Future Enhancements

- Multi-region key support for disaster recovery
- Customer-managed rotation schedules (90/180 days)
- Additional service principals (Lambda, SNS, etc.)
- Key usage alarms via CloudWatch
- Per-tenant key creation automation
