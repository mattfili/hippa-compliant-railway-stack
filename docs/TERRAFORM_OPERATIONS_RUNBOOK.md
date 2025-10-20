# Terraform Operations Runbook

Operational procedures for day-to-day infrastructure management and common administrative tasks.

## Table of Contents

1. [Common Operations](#common-operations)
2. [Scaling Operations](#scaling-operations)
3. [Security Operations](#security-operations)
4. [Maintenance Operations](#maintenance-operations)
5. [Monitoring and Alerts](#monitoring-and-alerts)
6. [Emergency Procedures](#emergency-procedures)

## Common Operations

### Add New AWS Config Rule

**When:** Need to monitor additional compliance requirements.

**Steps:**
```bash
# 1. Edit modules/config/main.tf
cat >> terraform/modules/config/main.tf << 'EOF'
resource "aws_config_config_rule" "encrypted_volumes" {
  name = "${var.environment}-encrypted-volumes"

  source {
    owner             = "AWS"
    source_identifier = "ENCRYPTED_VOLUMES"
  }

  depends_on = [aws_config_configuration_recorder.main]
}
EOF

# 2. Plan and apply
cd terraform
terraform workspace select production
terraform plan -var-file="terraform.tfvars.production" -out=tfplan
terraform apply tfplan

# 3. Verify rule is active
aws configservice describe-config-rules \
  --config-rule-names production-encrypted-volumes
```

---

### Rotate IAM Access Keys

**When:** Every 90 days (security best practice).

**Steps:**
```bash
# 1. Create new access key
aws iam create-access-key --user-name terraform-admin

# 2. Update Railway environment variables with new keys
# Railway Dashboard > Project > Variables

# 3. Test new credentials
export AWS_ACCESS_KEY_ID="new-key-id"
export AWS_SECRET_ACCESS_KEY="new-secret-key"
aws sts get-caller-identity

# 4. Update local AWS credentials
aws configure set aws_access_key_id "new-key-id"
aws configure set aws_secret_access_key "new-secret-key"

# 5. Deactivate old access key (after 24-hour grace period)
aws iam update-access-key \
  --user-name terraform-admin \
  --access-key-id "old-key-id" \
  --status Inactive

# 6. Delete old access key (after verification)
aws iam delete-access-key \
  --user-name terraform-admin \
  --access-key-id "old-key-id"
```

---

### Add New S3 Bucket

**When:** Need additional storage bucket for new feature.

**Steps:**
```bash
# 1. Edit modules/s3/main.tf
cat >> terraform/modules/s3/main.tf << 'EOF'
resource "aws_s3_bucket" "exports" {
  bucket        = "hipaa-compliant-exports-${var.environment}-${var.aws_account_id}"
  force_destroy = false

  tags = merge(var.tags, {
    Name = "exports-bucket"
  })
}

resource "aws_s3_bucket_versioning" "exports" {
  bucket = aws_s3_bucket.exports.id

  versioning_configuration {
    status = "Enabled"
  }
}
EOF

# 2. Add output in modules/s3/outputs.tf
cat >> terraform/modules/s3/outputs.tf << 'EOF'
output "s3_bucket_exports" {
  value       = aws_s3_bucket.exports.id
  description = "Exports bucket name"
}
EOF

# 3. Expose in root outputs.tf
cat >> terraform/outputs.tf << 'EOF'
output "s3_bucket_exports" {
  value       = module.s3.s3_bucket_exports
  description = "Exports bucket name"
}
EOF

# 4. Apply changes
terraform plan -var-file="terraform.tfvars.production" -out=tfplan
terraform apply tfplan

# 5. Update IAM policy to grant access (if needed)
```

---

### Modify Security Group Rules

**When:** Need to allow access from new IP range or service.

**Steps:**
```bash
# 1. Edit modules/networking/main.tf
# Add new ingress rule to appropriate security group

resource "aws_security_group_rule" "app_from_new_source" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["10.20.0.0/16"]  # New IP range
  security_group_id = aws_security_group.app.id
  description       = "Allow HTTPS from new source"
}

# 2. Plan and verify
terraform plan -var-file="terraform.tfvars.production"

# 3. Apply
terraform apply -var-file="terraform.tfvars.production"

# 4. Test connectivity
nc -zv <target-ip> 443
```

---

## Scaling Operations

### Scale RDS Vertically (Larger Instance Class)

**When:** Database CPU or memory consistently high.

**Steps:**
```bash
# 1. Create manual snapshot before scaling
aws rds create-db-snapshot \
  --db-instance-identifier hipaa-db-production \
  --db-snapshot-identifier pre-scale-$(date +%Y%m%d-%H%M%S)

# 2. Edit terraform.tfvars.production
# Change: rds_instance_class = "db.r6g.2xlarge"

# 3. Plan scaling change
terraform plan -var-file="terraform.tfvars.production" -out=tfplan

# 4. Schedule maintenance window (minimize downtime)
# RDS will restart during instance class change (5-15 minutes downtime)

# 5. Apply during maintenance window
terraform apply tfplan

# 6. Verify new instance class
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-production \
  --query 'DBInstances[0].[DBInstanceClass,DBInstanceStatus]'

# 7. Monitor performance post-scale
# Watch CloudWatch metrics for 24-48 hours
```

**Downtime:** 5-15 minutes (application unavailable during restart)

---

### Scale RDS Storage

**When:** Free storage space below 20%.

**Steps:**
```bash
# 1. Check current storage
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-production \
  --query 'DBInstances[0].[AllocatedStorage,StorageType]'

# 2. Edit terraform.tfvars.production
# Change: rds_allocated_storage = 200  # From 100

# 3. Plan storage increase
terraform plan -var-file="terraform.tfvars.production" -out=tfplan

# 4. Apply (NO downtime for storage increase)
terraform apply tfplan

# 5. Monitor storage increase
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-production \
  --query 'DBInstances[0].[AllocatedStorage,DBInstanceStatus]'
```

**Downtime:** None (storage increases do not require restart)

---

### Add Read Replica

**When:** Need to scale read capacity or improve disaster recovery.

**Steps:**
```bash
# 1. Edit terraform.tfvars.production
# Change: enable_read_replica = true

# 2. Plan replica creation
terraform plan -var-file="terraform.tfvars.production" -out=tfplan

# 3. Apply (creates replica, no downtime to primary)
terraform apply tfplan

# 4. Wait for replica to sync (10-30 minutes)
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-production-replica \
  --query 'DBInstances[0].[DBInstanceStatus,ReplicationSource]'

# 5. Update application to use reader endpoint
terraform output rds_reader_endpoint

# 6. Configure application read routing
# Update app/config.py to use reader endpoint for SELECT queries
```

**Downtime:** None

---

## Security Operations

### Rotate KMS Keys

**When:** Annually (automatic rotation) or on-demand for security incident.

**Steps:**
```bash
# Automatic rotation already enabled by Terraform
# To verify:
aws kms get-key-rotation-status \
  --key-id $(terraform output -raw kms_master_key_id)

# Manual rotation (creates new key material, old data still accessible):
# KMS handles this automatically - no action needed

# To disable/enable rotation:
aws kms enable-key-rotation \
  --key-id $(terraform output -raw kms_master_key_id)

# Verify rotation enabled
aws kms describe-key \
  --key-id $(terraform output -raw kms_master_key_id) \
  --query 'KeyMetadata.KeyRotationEnabled'
```

---

### Update SSL/TLS Certificate

**When:** Certificate expiration or security upgrade.

**Railway automatically manages certificates - no manual action**

For custom domains:
```bash
# Railway automatically provisions and renews Let's Encrypt certificates
# Verify certificate
curl -vI https://your-custom-domain.com 2>&1 | grep "expire date"
```

---

### Review and Update IAM Policies

**When:** Quarterly security review or application changes.

**Steps:**
```bash
# 1. Review current policies
aws iam get-role-policy \
  --role-name hipaa-app-backend-production \
  --policy-name production-s3-access-policy

# 2. Identify overly permissive policies
# Look for: wildcards (*) in Resource or Action fields

# 3. Edit modules/iam/main.tf to restrict policies

# 4. Plan and apply
terraform plan -var-file="terraform.tfvars.production" -out=tfplan
terraform apply tfplan

# 5. Test application still functions
curl https://your-railway-domain.railway.app/api/v1/health/ready
```

---

## Maintenance Operations

### Apply Terraform Updates

**When:** New Terraform or provider version released.

**Steps:**
```bash
# 1. Backup current state
aws s3 cp \
  s3://terraform-state-hipaa-${AWS_ACCOUNT_ID}/workspaces/production/hipaa-infrastructure/terraform.tfstate \
  terraform.tfstate.backup-$(date +%Y%m%d-%H%M%S)

# 2. Update versions.tf
# Change: required_version = ">= 1.6.0"
# Change: aws provider version = ">= 5.30"

# 3. Re-initialize
terraform init -upgrade

# 4. Plan (should show no changes to resources)
terraform plan -var-file="terraform.tfvars.production"

# 5. If plan shows unexpected changes, investigate before applying

# 6. Apply if safe
terraform apply -var-file="terraform.tfvars.production"
```

---

### Update RDS Parameter Group

**When:** Need to tune PostgreSQL performance parameters.

**Steps:**
```bash
# 1. Edit modules/rds/main.tf parameter group

resource "aws_db_parameter_group" "main" {
  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4096}"  # Increase from default
  }

  parameter {
    name  = "work_mem"
    value = "16384"  # 16MB, increase for complex queries
  }
}

# 2. Plan changes
terraform plan -var-file="terraform.tfvars.production" -out=tfplan

# 3. Apply (may require reboot for some parameters)
terraform apply tfplan

# 4. Check for pending reboot
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-production \
  --query 'DBInstances[0].PendingModifiedValues'

# 5. Schedule reboot during maintenance window if needed
aws rds reboot-db-instance \
  --db-instance-identifier hipaa-db-production
```

---

### Patch RDS Minor Version

**When:** Security patches or bug fixes released.

**Steps:**
```bash
# 1. Check current version
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-production \
  --query 'DBInstances[0].[EngineVersion,AutoMinorVersionUpgrade]'

# 2. Enable auto minor version upgrade (recommended)
# Already enabled in Terraform: auto_minor_version_upgrade = true

# 3. Manual upgrade to specific version
aws rds modify-db-instance \
  --db-instance-identifier hipaa-db-production \
  --engine-version 15.5 \
  --apply-immediately

# 4. Monitor upgrade
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-production \
  --query 'DBInstances[0].[EngineVersion,DBInstanceStatus]'
```

---

## Monitoring and Alerts

### Set Up CloudWatch Alarms for RDS

**Steps:**
```bash
# Create alarm for high CPU
aws cloudwatch put-metric-alarm \
  --alarm-name hipaa-db-production-high-cpu \
  --alarm-description "Alert when RDS CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=DBInstanceIdentifier,Value=hipaa-db-production \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:devops-alerts

# Create alarm for low storage
aws cloudwatch put-metric-alarm \
  --alarm-name hipaa-db-production-low-storage \
  --alarm-description "Alert when free storage < 10GB" \
  --metric-name FreeStorageSpace \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 10737418240 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=DBInstanceIdentifier,Value=hipaa-db-production \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:devops-alerts
```

---

### Review AWS Config Compliance

**Daily:**
```bash
# Check overall compliance status
aws configservice describe-compliance-by-config-rule \
  --query 'ComplianceByConfigRules[*].[ConfigRuleName,Compliance.ComplianceType]' \
  --output table

# List non-compliant resources
aws configservice describe-compliance-by-config-rule \
  --compliance-types NON_COMPLIANT \
  --query 'ComplianceByConfigRules[*].[ConfigRuleName]' \
  --output text | while read rule; do
    echo "Non-compliant rule: $rule"
    aws configservice get-compliance-details-by-config-rule \
      --config-rule-name "$rule" \
      --compliance-types NON_COMPLIANT
  done
```

---

### Monitor Terraform Drift

**Weekly:**
```bash
# Refresh state
terraform refresh -var-file="terraform.tfvars.production"

# Detect drift
terraform plan -var-file="terraform.tfvars.production" -detailed-exitcode

# Exit codes:
# 0 = No changes
# 1 = Error
# 2 = Changes detected (drift)

# If drift detected, investigate and remediate:
terraform apply -var-file="terraform.tfvars.production"
```

---

## Emergency Procedures

### Emergency: RDS Instance Failure

**Steps:**
```bash
# 1. Check Multi-AZ automatic failover (should happen automatically)
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-production \
  --query 'DBInstances[0].[DBInstanceStatus,MultiAZ,SecondaryAvailabilityZone]'

# 2. If Multi-AZ, wait 1-2 minutes for automatic failover

# 3. If no failover or single-AZ, promote read replica
aws rds promote-read-replica \
  --db-instance-identifier hipaa-db-production-replica

# 4. Update application connection string
terraform output rds_reader_endpoint  # Now primary

# 5. Update Railway DATABASE_URL environment variable
```

---

### Emergency: S3 Bucket Access Denied

**Steps:**
```bash
# 1. Verify IAM role permissions
aws iam get-role-policy \
  --role-name hipaa-app-backend-production \
  --policy-name production-s3-access-policy

# 2. Verify bucket policy
aws s3api get-bucket-policy \
  --bucket $(terraform output -raw s3_bucket_documents)

# 3. Check KMS key access
aws kms get-key-policy \
  --key-id $(terraform output -raw kms_master_key_id) \
  --policy-name default

# 4. Test access with AWS CLI
aws s3 ls s3://$(terraform output -raw s3_bucket_documents)

# 5. If still failing, temporarily add broader permissions, then narrow down
```

---

### Emergency: Cost Spike

**Steps:**
```bash
# 1. Check Cost Explorer for spike
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics UnblendedCost \
  --group-by Type=SERVICE

# 2. Identify service causing spike
# Common culprits: Data transfer, NAT Gateway, RDS storage

# 3. Immediate actions:
# - Stop non-production RDS instances
# - Reduce NAT gateway count to 1 (dev only)
# - Check for runaway Lambda/EC2 instances

# 4. Emergency infrastructure scale-down
terraform workspace select dev
terraform destroy -var-file="terraform.tfvars.dev"
```

---

## Scheduled Maintenance

### Daily Checklist

- [ ] Review CloudWatch alarms
- [ ] Check AWS Config compliance status
- [ ] Verify automated RDS backups completed
- [ ] Monitor application error rates

### Weekly Checklist

- [ ] Run `terraform plan` to detect drift
- [ ] Review Cost Explorer for anomalies
- [ ] Check RDS Performance Insights
- [ ] Review security group rules for changes

### Monthly Checklist

- [ ] Review and optimize RDS instance sizing
- [ ] Delete old RDS snapshots (>90 days)
- [ ] Review IAM policies for overly permissive rules
- [ ] Update documentation with operational changes

### Quarterly Checklist

- [ ] Rotate IAM access keys
- [ ] Review Reserved Instance opportunities
- [ ] Perform disaster recovery drill
- [ ] Update Terraform and provider versions

---

## Contact Information

**On-Call Rotation:** [PagerDuty/OpsGenie link]
**Slack Channel:** #infrastructure-alerts
**Email:** devops-team@organization.com

**Escalation:**
- Level 1: DevOps Engineer (15-minute response)
- Level 2: Infrastructure Lead (30-minute response)
- Level 3: CTO (1-hour response)

---

## Additional Resources

- AWS Console: https://console.aws.amazon.com/
- Terraform Documentation: https://www.terraform.io/docs
- Internal Wiki: [Link to internal documentation]
- Runbook Repository: [Link to GitLab/GitHub runbooks]
