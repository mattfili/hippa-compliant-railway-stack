# AWS Config Module

## Overview

This Terraform module deploys AWS Config for continuous compliance monitoring and alerting. It implements managed Config rules specifically designed to detect HIPAA compliance violations, ensuring that infrastructure resources maintain required security standards.

## Purpose

AWS Config provides:
- **Configuration Management**: Tracks all resource configuration changes over time
- **Compliance Monitoring**: Continuously evaluates resources against HIPAA security rules
- **Violation Alerting**: Sends SNS notifications when resources become non-compliant
- **Audit Trail**: Maintains detailed configuration history in S3 for compliance audits

## Features

### AWS Config Rules Deployed

This module deploys 6 managed Config rules for HIPAA compliance:

1. **S3 Bucket Encryption Enabled**
   - Rule ID: `S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED`
   - Purpose: Ensures all S3 buckets have server-side encryption enabled
   - HIPAA Requirement: Encryption at rest (164.312(a)(2)(iv))

2. **RDS Storage Encrypted**
   - Rule ID: `RDS_STORAGE_ENCRYPTED`
   - Purpose: Verifies RDS instances have encryption at rest enabled
   - HIPAA Requirement: Encryption at rest (164.312(a)(2)(iv))

3. **RDS Instance Public Access Check**
   - Rule ID: `RDS_INSTANCE_PUBLIC_ACCESS_CHECK`
   - Purpose: Detects publicly accessible RDS instances
   - HIPAA Requirement: Access controls (164.312(a)(1))

4. **IAM Policy No Statements With Admin Access**
   - Rule ID: `IAM_POLICY_NO_STATEMENTS_WITH_ADMIN_ACCESS`
   - Purpose: Identifies overly permissive IAM policies
   - HIPAA Requirement: Least privilege access (164.308(a)(4))

5. **CloudTrail Enabled**
   - Rule ID: `CLOUD_TRAIL_ENABLED`
   - Purpose: Ensures CloudTrail logging is active
   - HIPAA Requirement: Audit controls (164.312(b))

6. **VPC Security Groups Open Only to Authorized Ports**
   - Rule ID: `VPC_SG_OPEN_ONLY_TO_AUTHORIZED_PORTS`
   - Purpose: Detects security groups with unrestricted access
   - HIPAA Requirement: Access controls (164.312(a)(1))
   - Authorized Ports: 443 (HTTPS), 5432 (PostgreSQL)

### Configuration Recording

- **Recording Scope**: All supported AWS resources
- **Global Resources**: Included (IAM, CloudFront, Route53)
- **Recording Mode**: Continuous
- **Snapshot Frequency**: Daily (24 hours)

### SNS Alerting

- **SNS Topic**: Created for Config compliance notifications
- **Email Subscription**: Optional (configured via `sns_alert_email` variable)
- **Alert Triggers**: Non-compliant resource evaluations
- **Notification Format**: JSON containing rule name, resource, and compliance status

## Usage

### Basic Usage

```hcl
module "config" {
  source = "./modules/config"

  environment           = "production"
  s3_bucket_audit_logs  = "hipaa-compliant-audit-prod-123456789012"
  sns_alert_email       = "security-team@example.com"

  tags = {
    Project = "HIPAA Compliant Stack"
    Owner   = "Security Team"
  }
}
```

### Without Email Notifications

```hcl
module "config" {
  source = "./modules/config"

  environment           = "dev"
  s3_bucket_audit_logs  = "hipaa-compliant-audit-dev-123456789012"

  # No email alerts for dev environment
  sns_alert_email       = ""
}
```

### With Auto-Remediation (Future Enhancement)

```hcl
module "config" {
  source = "./modules/config"

  environment              = "production"
  s3_bucket_audit_logs     = "hipaa-compliant-audit-prod-123456789012"
  enable_auto_remediation  = true  # Not currently implemented

  tags = {
    AutoRemediation = "Enabled"
  }
}
```

## Input Variables

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `environment` | string | Yes | - | Environment name (dev, staging, production) |
| `s3_bucket_audit_logs` | string | Yes | - | S3 bucket name for Config snapshots |
| `sns_alert_email` | string | No | "" | Email address for compliance alerts |
| `enable_auto_remediation` | bool | No | false | Enable automatic remediation (safety disabled) |
| `tags` | map(string) | No | {} | Additional resource tags |

## Output Values

| Output | Type | Description |
|--------|------|-------------|
| `config_recorder_name` | string | Name of the Config recorder |
| `config_recorder_role_arn` | string | ARN of the IAM role used by Config |
| `config_sns_topic_arn` | string | ARN of the SNS topic for alerts |
| `config_delivery_channel_name` | string | Name of the Config delivery channel |
| `config_rules` | map(string) | Map of all deployed Config rule names |

## Dependencies

### Required Modules

- **S3 Module**: This module requires the audit logs bucket from the S3 module
  - Bucket must exist before deploying Config
  - Bucket must have versioning enabled
  - Config IAM role requires PutObject permission

### AWS Services

- **AWS Config**: Core compliance monitoring service
- **S3**: Storage for configuration snapshots
- **SNS**: Notification delivery for compliance violations
- **IAM**: Service role for Config permissions

## IAM Permissions

### Config Service Role

The module creates an IAM role with the following permissions:

1. **AWS Managed Policy**: `ConfigRole`
   - Allows Config to describe and list AWS resources
   - Required for configuration recording

2. **Custom S3 Policy**: Access to audit logs bucket
   - `s3:PutObject` - Write configuration snapshots
   - `s3:PutObjectAcl` - Set object ACLs (bucket-owner-full-control)
   - `s3:GetBucketVersioning` - Verify bucket versioning

3. **SNS Publish**: Allows Config to publish to SNS topic
   - Configured via SNS topic policy

## HIPAA Compliance Mapping

### Administrative Safeguards

- **164.308(a)(1)(ii)(D)** - Information System Activity Review
  - Config rules continuously monitor resource configurations
  - Configuration history provides audit trail

### Technical Safeguards

- **164.312(a)(1)** - Access Control
  - Rules detect public RDS instances and unrestricted security groups

- **164.312(a)(2)(iv)** - Encryption and Decryption
  - Rules verify S3 and RDS encryption enabled

- **164.312(b)** - Audit Controls
  - Config recording provides comprehensive audit logs
  - CloudTrail enabled rule ensures logging active

## Alert Configuration

### Email Subscription Setup

1. Apply Terraform configuration with `sns_alert_email` set
2. AWS sends confirmation email to the specified address
3. Click confirmation link in email to activate subscription
4. Alerts will be sent to email for non-compliant resources

### Alert Email Format

```json
{
  "configRuleName": "production-s3-bucket-encryption-enabled",
  "resourceType": "AWS::S3::Bucket",
  "resourceId": "my-bucket-name",
  "complianceType": "NON_COMPLIANT",
  "messageType": "ComplianceChangeNotification",
  "notificationCreationTime": "2025-10-17T12:00:00.000Z"
}
```

### Handling Alerts

1. **Review Notification**: Identify non-compliant resource
2. **Investigate Root Cause**: Check AWS Console or CLI for resource configuration
3. **Remediate**: Apply necessary configuration changes
4. **Verify**: Config re-evaluates resource automatically (24-hour cycle or manual trigger)
5. **Document**: Record remediation actions for compliance audit

## Cost Considerations

### AWS Config Pricing (US East 1)

- **Configuration Items**: $0.003 per item recorded
- **Config Rule Evaluations**: $0.001 per evaluation
- **Config Snapshots**: Storage in S3 (standard rates)

### Estimated Monthly Costs

| Environment | Resources | Config Items | Rules | Monthly Cost |
|-------------|-----------|--------------|-------|--------------|
| Development | ~50 | ~1500 | 6 | ~$10 |
| Staging | ~100 | ~3000 | 6 | ~$18 |
| Production | ~200 | ~6000 | 6 | ~$35 |

**Note**: Costs vary based on configuration change frequency and resource count.

## Operations

### Manually Trigger Config Evaluation

```bash
# Trigger all rules for a specific resource
aws configservice start-config-rules-evaluation \
  --config-rule-names production-s3-bucket-encryption-enabled

# Trigger evaluation for specific resource
aws configservice deliver-config-snapshot \
  --delivery-channel-name production-config-delivery-channel
```

### View Compliance Status

```bash
# List all Config rules and their compliance status
aws configservice describe-compliance-by-config-rule \
  --config-rule-names production-s3-bucket-encryption-enabled

# Get compliance details for a specific resource
aws configservice get-compliance-details-by-resource \
  --resource-type AWS::S3::Bucket \
  --resource-id my-bucket-name
```

### Access Configuration History

Configuration snapshots are stored in S3 at:
```
s3://hipaa-compliant-audit-{env}-{account-id}/AWSLogs/{account-id}/Config/{region}/
```

## Troubleshooting

### Config Recorder Not Starting

**Issue**: Config recorder shows as stopped in AWS Console

**Solution**:
1. Verify S3 bucket exists and is accessible
2. Check IAM role permissions for S3 PutObject
3. Ensure delivery channel is properly configured
4. Restart recorder:
   ```bash
   aws configservice start-configuration-recorder \
     --configuration-recorder-name production-config-recorder
   ```

### Rules Not Evaluating

**Issue**: Config rules remain in "No data" state

**Solution**:
1. Wait 24 hours for initial evaluation cycle
2. Verify Config recorder is running
3. Check if resources exist in scope of rule
4. Manually trigger evaluation (see Operations section)

### Email Alerts Not Received

**Issue**: SNS subscription created but no emails received

**Solution**:
1. Check email inbox (including spam/junk folder) for confirmation email
2. Verify SNS topic subscription status:
   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn arn:aws:sns:us-east-1:123456789012:production-config-alerts
   ```
3. Confirm subscription status is "Confirmed" (not "PendingConfirmation")
4. Test SNS topic manually:
   ```bash
   aws sns publish \
     --topic-arn arn:aws:sns:us-east-1:123456789012:production-config-alerts \
     --message "Test message"
   ```

### S3 Access Denied Errors

**Issue**: Config fails to write to S3 bucket

**Solution**:
1. Verify S3 bucket policy allows Config service
2. Check IAM role has correct S3 permissions
3. Ensure bucket is in same region as Config
4. Review S3 bucket policy:
   ```bash
   aws s3api get-bucket-policy --bucket hipaa-compliant-audit-prod-123456789012
   ```

## Security Considerations

### Least Privilege IAM

- Config IAM role has minimal permissions required for operation
- S3 policy scoped to specific bucket and prefix
- SNS publish permission limited to Config service

### Audit Trail Protection

- Configuration snapshots stored in immutable S3 bucket
- S3 versioning should be enabled on audit bucket
- Consider enabling S3 Object Lock for compliance requirements

### Alert Confidentiality

- SNS email alerts contain resource IDs and compliance status
- Do not include sensitive data in resource tags (visible in alerts)
- Consider using SNS → Lambda → Slack/PagerDuty for sensitive environments

## Future Enhancements

### Auto-Remediation (Not Currently Implemented)

AWS Config supports automatic remediation using Systems Manager Automation documents. This feature is disabled by default for safety but can be enabled in future iterations:

1. **Remediation Actions**:
   - Auto-enable S3 encryption on non-compliant buckets
   - Auto-disable public RDS instances
   - Auto-restrict overly permissive security groups

2. **Implementation Approach**:
   - Create SSM Automation documents
   - Attach remediation configurations to Config rules
   - Set `enable_auto_remediation = true`

3. **Safety Considerations**:
   - Test thoroughly in development environment
   - Implement approval workflows for production
   - Monitor remediation actions via CloudWatch

### Additional Config Rules

Consider adding more rules for comprehensive compliance:

- `encrypted-volumes` - Detect unencrypted EBS volumes
- `vpc-flow-logs-enabled` - Verify VPC Flow Logs active
- `multi-region-cloudtrail-enabled` - Ensure CloudTrail covers all regions
- `access-keys-rotated` - Detect old IAM access keys

### Custom Config Rules

For organization-specific requirements, create custom Lambda-based Config rules:

- Verify specific tagging standards
- Validate resource naming conventions
- Check custom encryption key usage
- Enforce tenant isolation policies

## Additional Resources

- [AWS Config Documentation](https://docs.aws.amazon.com/config/)
- [AWS Config Managed Rules Reference](https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html)
- [HIPAA Compliance Whitepaper](https://docs.aws.amazon.com/whitepapers/latest/architecting-hipaa-security-and-compliance-on-aws/)
- [AWS Config Best Practices](https://docs.aws.amazon.com/config/latest/developerguide/best-practices.html)

## Support

For issues or questions about this module:
1. Review troubleshooting section above
2. Check AWS Config service health status
3. Consult AWS Config documentation
4. Contact infrastructure team for module-specific questions
