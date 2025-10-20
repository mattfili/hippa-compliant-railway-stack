# Terraform Disaster Recovery Procedures

Complete disaster recovery and rollback procedures for AWS infrastructure managed with Terraform.

## Table of Contents

1. [Overview](#overview)
2. [RDS Disaster Recovery](#rds-disaster-recovery)
3. [S3 Disaster Recovery](#s3-disaster-recovery)
4. [Terraform State Recovery](#terraform-state-recovery)
5. [Complete Infrastructure Rollback](#complete-infrastructure-rollback)
6. [Testing DR Procedures](#testing-dr-procedures)
7. [RTO and RPO Targets](#rto-and-rpo-targets)

## Overview

### Backup Strategy Summary

| Component | Backup Method | Frequency | Retention | Location |
|-----------|---------------|-----------|-----------|----------|
| RDS PostgreSQL | Automated snapshots | Daily | 30 days | Same region (Multi-AZ) |
| RDS PostgreSQL | Manual snapshots | Before changes | Indefinite | Same region |
| S3 Objects | Versioning | Per object write | 7 years | Same bucket |
| S3 Objects | Lifecycle to Glacier | After 365 days | 7 years | Same region |
| Terraform State | S3 versioning | Per state change | Indefinite | S3 state bucket |
| Application Data | RDS + S3 combined | Daily (RDS) / Real-time (S3) | 30 days / 7 years | AWS |

### Recovery Objectives

**Recovery Time Objective (RTO):**
- **RDS Snapshot Restore:** 10-30 minutes (depends on database size)
- **RDS Point-in-Time Restore:** 10-30 minutes
- **S3 Object Recovery:** < 5 minutes
- **Terraform State Recovery:** < 5 minutes
- **Complete Infrastructure Rebuild:** 15-25 minutes

**Recovery Point Objective (RPO):**
- **RDS Automated Backups:** Up to 5 minutes (PITR granularity)
- **RDS Manual Snapshots:** Time of snapshot creation
- **S3 Versioning:** 0 seconds (immediate versioning)
- **Terraform State:** Per state change (typically minutes)

## RDS Disaster Recovery

### Scenario 1: Recover from Automated Backup (Recent Data Loss)

**Use Case:** Accidental data deletion, need to restore to recent point in time.

**Steps:**

1. **Identify Target Restore Point:**
```bash
# List recent automated snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --snapshot-type automated \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime,Status]' \
  --output table

# Or describe instance for last automated backup time
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --query 'DBInstances[0].[LatestRestorableTime,BackupRetentionPeriod]' \
  --output table
```

2. **Create Manual Snapshot of Current State (Precaution):**
```bash
aws rds create-db-snapshot \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --db-snapshot-identifier pre-restore-$(date +%Y%m%d-%H%M%S)

# Wait for snapshot to complete
aws rds wait db-snapshot-completed \
  --db-snapshot-identifier pre-restore-$(date +%Y%m%d-%H%M%S)
```

3. **Restore to Point in Time (Creates New Instance):**
```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier hipaa-db-$(terraform workspace show) \
  --target-db-instance-identifier hipaa-db-$(terraform workspace show)-restored \
  --restore-time "2025-10-17T10:30:00Z" \
  --db-subnet-group-name $(terraform workspace show)-rds-subnet-group \
  --publicly-accessible false \
  --multi-az $([ "$(terraform workspace show)" = "production" ] && echo "true" || echo "false")

# Wait for restore to complete (10-30 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier hipaa-db-$(terraform workspace show)-restored
```

4. **Update Application Connection String:**

**Option A: Update Terraform to Manage Restored Instance**
```bash
# Import restored instance into Terraform state
terraform import module.rds.aws_db_instance.main hipaa-db-$(terraform workspace show)-restored

# Update terraform.tfvars to use restored instance identifier
# Re-apply to update outputs
terraform apply -var-file="terraform.tfvars.$(terraform workspace show)"

# Update Railway environment variables with new endpoint
terraform output -json > outputs.json
# Upload to Railway or re-deploy to load new outputs
```

**Option B: Update DNS/Connection Strings Manually**
```bash
# Get restored instance endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-$(terraform workspace show)-restored \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# Update Railway environment variable DATABASE_URL manually
echo "Update Railway DATABASE_URL to: postgresql://user:pass@$RDS_ENDPOINT:5432/hipaa_db"
```

5. **Verify Data and Application Connectivity:**
```bash
# Test connection from application
curl https://your-railway-domain.railway.app/api/v1/health/ready

# Verify critical data restored
psql -h $RDS_ENDPOINT -U admin_user -d hipaa_db -c "SELECT COUNT(*) FROM documents;"
```

6. **Delete Original Instance (After Verification):**
```bash
# Create final snapshot before deletion
aws rds create-db-snapshot \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --db-snapshot-identifier final-before-delete-$(date +%Y%m%d-%H%M%S)

# Delete original instance
aws rds delete-db-instance \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --skip-final-snapshot  # Already created manual snapshot above
```

---

### Scenario 2: Restore from Manual Snapshot (After Major Incident)

**Use Case:** Database corruption, major data loss, need to restore from known-good snapshot.

**Steps:**

1. **List Available Manual Snapshots:**
```bash
aws rds describe-db-snapshots \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --snapshot-type manual \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime,Status,SnapshotType]' \
  --output table | sort -k2 -r
```

2. **Restore from Specific Snapshot:**
```bash
# Restore from snapshot (creates new instance)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier hipaa-db-$(terraform workspace show)-recovered \
  --db-snapshot-identifier manual-snapshot-20251017-100000 \
  --db-subnet-group-name $(terraform workspace show)-rds-subnet-group \
  --publicly-accessible false \
  --multi-az $([ "$(terraform workspace show)" = "production" ] && echo "true" || echo "false")

# Wait for restore (10-30 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier hipaa-db-$(terraform workspace show)-recovered
```

3. **Verify Restored Data:**
```bash
# Connect to restored instance
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-$(terraform workspace show)-recovered \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# Check data integrity
psql -h $RDS_ENDPOINT -U admin_user -d hipaa_db << EOF
SELECT COUNT(*) FROM tenants;
SELECT COUNT(*) FROM documents;
SELECT MAX(created_at) FROM audit_logs;
EOF

# Verify latest data timestamp matches expected snapshot time
```

4. **Update Application and Clean Up (Same as Scenario 1, Steps 4-6)**

---

### Scenario 3: Promote Read Replica (Production Only)

**Use Case:** Primary RDS instance failure, need immediate failover.

**Steps:**

1. **Verify Read Replica Exists and Is Healthy:**
```bash
aws rds describe-db-instances \
  --filters "Name=db-instance-id,Values=*replica*" \
  --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceStatus,ReadReplicaSourceDBInstanceIdentifier]' \
  --output table
```

2. **Promote Read Replica to Standalone:**
```bash
# Promote replica to independent instance
aws rds promote-read-replica \
  --db-instance-identifier hipaa-db-production-replica

# Wait for promotion to complete (5-10 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier hipaa-db-production-replica
```

3. **Update Application Connection:**
```bash
# Get promoted replica endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-production-replica \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# Update Railway DATABASE_URL immediately
echo "New RDS endpoint: $RDS_ENDPOINT"

# Update Terraform to manage promoted replica
terraform import module.rds.aws_db_instance.main hipaa-db-production-replica
```

4. **Create New Read Replica (After Stabilization):**
```bash
# After application stabilizes on promoted replica, create new read replica
# This is done through Terraform:
terraform apply -var-file="terraform.tfvars.production"
```

5. **Clean Up Failed Primary (After Verification):**
```bash
# Create final snapshot of failed primary (if accessible)
aws rds create-db-snapshot \
  --db-instance-identifier hipaa-db-production \
  --db-snapshot-identifier failed-primary-final-$(date +%Y%m%d-%H%M%S)

# Delete failed primary
aws rds delete-db-instance \
  --db-instance-identifier hipaa-db-production \
  --final-db-snapshot-identifier failed-primary-final-$(date +%Y%m%d-%H%M%S)
```

---

## S3 Disaster Recovery

### Scenario 1: Recover Deleted S3 Object

**Use Case:** Document accidentally deleted, need to restore from version history.

**Steps:**

1. **List Object Versions:**
```bash
S3_BUCKET=$(terraform output -raw s3_bucket_documents)

# List all versions of specific object
aws s3api list-object-versions \
  --bucket $S3_BUCKET \
  --prefix tenants/acme-healthcare/documents/report.pdf \
  --query 'Versions[*].[VersionId,LastModified,IsLatest]' \
  --output table
```

2. **Restore Previous Version:**
```bash
# Copy previous version to restore it as current
aws s3api copy-object \
  --copy-source "$S3_BUCKET/tenants/acme-healthcare/documents/report.pdf?versionId=<version-id>" \
  --bucket $S3_BUCKET \
  --key tenants/acme-healthcare/documents/report.pdf \
  --metadata-directive COPY \
  --server-side-encryption aws:kms \
  --ssekms-key-id $(terraform output -raw kms_master_key_id)
```

3. **Verify Restoration:**
```bash
# List current version
aws s3api head-object \
  --bucket $S3_BUCKET \
  --key tenants/acme-healthcare/documents/report.pdf

# Download and verify content
aws s3 cp "s3://$S3_BUCKET/tenants/acme-healthcare/documents/report.pdf" ./restored-report.pdf
```

4. **Alternative: Delete Delete Marker (If Object Appears Deleted):**
```bash
# If object has delete marker, remove it
aws s3api list-object-versions \
  --bucket $S3_BUCKET \
  --prefix tenants/acme-healthcare/documents/report.pdf \
  --query 'DeleteMarkers[*].[VersionId,IsLatest]'

# Delete the delete marker
aws s3api delete-object \
  --bucket $S3_BUCKET \
  --key tenants/acme-healthcare/documents/report.pdf \
  --version-id <delete-marker-version-id>

# Object now accessible again (previous version becomes current)
```

---

### Scenario 2: Restore Entire Bucket from Lifecycle Glacier

**Use Case:** Need to restore archived documents that transitioned to Glacier.

**Steps:**

1. **List Archived Objects:**
```bash
S3_BUCKET=$(terraform output -raw s3_bucket_documents)

# List objects in Glacier storage class
aws s3api list-objects-v2 \
  --bucket $S3_BUCKET \
  --query 'Contents[?StorageClass==`GLACIER`].[Key,LastModified,Size]' \
  --output table
```

2. **Initiate Glacier Restore Request:**
```bash
# Restore single object (Expedited: 1-5 min, Standard: 3-5 hours, Bulk: 5-12 hours)
aws s3api restore-object \
  --bucket $S3_BUCKET \
  --key tenants/acme-healthcare/documents/archived-report.pdf \
  --restore-request '{
    "Days": 7,
    "GlacierJobParameters": {
      "Tier": "Standard"
    }
  }'

# Restore multiple objects with AWS CLI batch script
for key in $(aws s3api list-objects-v2 \
  --bucket $S3_BUCKET \
  --prefix tenants/acme-healthcare/ \
  --query 'Contents[?StorageClass==`GLACIER`].Key' \
  --output text); do
  aws s3api restore-object \
    --bucket $S3_BUCKET \
    --key "$key" \
    --restore-request '{"Days": 7, "GlacierJobParameters": {"Tier": "Standard"}}'
  echo "Restore initiated for $key"
done
```

3. **Check Restore Status:**
```bash
# Check if restore is complete
aws s3api head-object \
  --bucket $S3_BUCKET \
  --key tenants/acme-healthcare/documents/archived-report.pdf \
  --query 'Restore'

# Output: 'ongoing-request="true"' (still restoring) or restoration completed date
```

4. **Access Restored Object:**
```bash
# After restoration completes (check status above)
# Object is accessible via normal S3 API for specified duration (7 days in example)

aws s3 cp "s3://$S3_BUCKET/tenants/acme-healthcare/documents/archived-report.pdf" ./restored.pdf

# Note: Object remains in Glacier; this creates temporary copy in S3 Standard
```

---

### Scenario 3: Recover from Accidental Bucket Deletion

**Use Case:** S3 bucket accidentally deleted (unlikely due to force_destroy=false, but possible manually).

**Recovery:**
- **PREVENTION:** Terraform configures `force_destroy = false` on all buckets
- **DETECTION:** AWS Config rule detects bucket deletion immediately
- **RECOVERY:** Cannot recover deleted bucket, but versioning protects objects

**If Bucket Deleted Despite Protections:**
```bash
# 1. Contact AWS Support immediately (within 24 hours for best chance)
# 2. Provide bucket name, account ID, and approximate deletion time
# 3. AWS may be able to recover bucket and objects

# 4. If AWS cannot recover, recreate bucket via Terraform
terraform apply -var-file="terraform.tfvars.$(terraform workspace show)"

# 5. Objects are LOST unless you have external backups
# LESSON: Always maintain cross-region replication or external backups for critical data
```

---

## Terraform State Recovery

### Scenario 1: Restore Previous Terraform State Version

**Use Case:** Terraform state corrupted or incorrect after failed apply.

**Steps:**

1. **Backup Current State (Even If Corrupted):**
```bash
cp .terraform/terraform.tfstate terraform.tfstate.corrupted.$(date +%Y%m%d-%H%M%S)
```

2. **List Available State Versions in S3:**
```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws s3api list-object-versions \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --prefix workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate \
  --query 'Versions[*].[VersionId,LastModified,Size]' \
  --output table | head -20
```

3. **Download Previous Working Version:**
```bash
# Select version ID from list above
PREVIOUS_VERSION_ID="<version-id>"

aws s3api get-object \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --key workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate \
  --version-id $PREVIOUS_VERSION_ID \
  terraform.tfstate.recovered
```

4. **Verify Recovered State:**
```bash
# Validate JSON structure
jq . terraform.tfstate.recovered > /dev/null && echo "Valid JSON" || echo "Invalid JSON"

# Check Terraform can read it
terraform show -json terraform.tfstate.recovered | jq -r '.values.root_module.resources[].address' | head -10
```

5. **Replace Current State:**
```bash
# Backup current state to S3 (manual backup)
aws s3 cp .terraform/terraform.tfstate \
  s3://terraform-state-hipaa-${AWS_ACCOUNT_ID}/manual-backups/corrupted-$(date +%Y%m%d-%H%M%S).tfstate

# Replace with recovered state
cp terraform.tfstate.recovered .terraform/terraform.tfstate
```

6. **Refresh and Verify:**
```bash
# Refresh state to sync with reality
terraform refresh -var-file="terraform.tfvars.$(terraform workspace show)"

# Plan to verify minimal changes
terraform plan -var-file="terraform.tfvars.$(terraform workspace show)"

# If plan shows only expected changes, state recovered successfully
```

---

### Scenario 2: Rebuild State from Scratch (Last Resort)

**Use Case:** State file completely lost or unrecoverable, must recreate from AWS resources.

**Steps:**

1. **Create New Empty State:**
```bash
# Backup any existing state
mv .terraform terraform.old.$(date +%Y%m%d-%H%M%S)

# Re-initialize Terraform
terraform init
```

2. **Import Resources Systematically:**
```bash
# Start with foundational resources (VPC, subnets)
terraform import module.vpc.aws_vpc.main vpc-xxxxx
terraform import 'module.vpc.aws_subnet.public[0]' subnet-xxxxx
terraform import 'module.vpc.aws_subnet.public[1]' subnet-yyyyy
# ... continue for all resources

# Import KMS key
terraform import module.kms.aws_kms_key.master arn:aws:kms:us-east-1:123456789012:key/xxxxx

# Import RDS instance
terraform import module.rds.aws_db_instance.main hipaa-db-production

# Import S3 buckets
terraform import module.s3.aws_s3_bucket.documents hipaa-compliant-docs-production-123456789012

# Import IAM resources
terraform import module.iam.aws_iam_role.backend_app hipaa-app-backend-production

# ... continue for all resources
```

3. **Verify Imports:**
```bash
# After each import, verify in state
terraform state list

# Plan should show minimal changes (only metadata)
terraform plan -var-file="terraform.tfvars.$(terraform workspace show)"
```

4. **Document Imports:**
```bash
# Create script for future reference
cat > import-resources.sh << 'EOF'
#!/bin/bash
# Resource import script for disaster recovery
# Run this script if Terraform state is lost

terraform import module.vpc.aws_vpc.main vpc-xxxxx
terraform import 'module.vpc.aws_subnet.public[0]' subnet-xxxxx
# ... all imports
EOF

chmod +x import-resources.sh
```

---

## Complete Infrastructure Rollback

### Scenario 1: Rollback to Previous Terraform Configuration

**Use Case:** Recent Terraform changes caused issues, need to revert to previous working configuration.

**Steps:**

1. **Identify Last Working Commit:**
```bash
# List recent Git commits
git log --oneline terraform/ | head -10

# Or check recent Terraform state versions
aws s3api list-object-versions \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --prefix workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate \
  --query 'Versions[*].[VersionId,LastModified]' \
  --output table | head -10
```

2. **Revert Terraform Code:**
```bash
# Option A: Git revert to specific commit
git revert <commit-hash>
git push origin main

# Option B: Git reset to specific commit (destructive)
git reset --hard <commit-hash>
git push --force origin main

# Option C: Checkout specific commit
git checkout <commit-hash> terraform/
git commit -m "Rollback Terraform to working state"
git push origin main
```

3. **Plan Rollback:**
```bash
terraform plan -var-file="terraform.tfvars.$(terraform workspace show)" -out=rollback.tfplan

# Review plan carefully:
# - Resources to be destroyed
# - Resources to be created
# - Resources to be modified
```

4. **Execute Rollback:**
```bash
# Create manual RDS snapshot before any destructive changes
aws rds create-db-snapshot \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --db-snapshot-identifier pre-rollback-$(date +%Y%m%d-%H%M%S)

# Apply rollback
terraform apply rollback.tfplan

# Monitor for errors
```

5. **Verify Rollback:**
```bash
# Check application health
curl https://your-railway-domain.railway.app/api/v1/health/ready

# Verify RDS connectivity
terraform output rds_endpoint

# Verify S3 buckets accessible
aws s3 ls s3://$(terraform output -raw s3_bucket_documents)
```

---

### Scenario 2: Emergency Infrastructure Shutdown

**Use Case:** Security incident or cost containment, need to shut down infrastructure immediately.

**Steps:**

1. **Create Comprehensive Backups:**
```bash
# RDS snapshot
aws rds create-db-snapshot \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --db-snapshot-identifier emergency-shutdown-$(date +%Y%m%d-%H%M%S)

# Wait for snapshot
aws rds wait db-snapshot-completed \
  --db-snapshot-identifier emergency-shutdown-$(date +%Y%m%d-%H%M%S)

# S3 buckets already have versioning (protected)

# Terraform state already versioned in S3 (protected)
```

2. **Destroy Infrastructure:**
```bash
# Review what will be destroyed
terraform plan -destroy -var-file="terraform.tfvars.$(terraform workspace show)"

# Destroy (keep backups)
terraform destroy -var-file="terraform.tfvars.$(terraform workspace show)"

# Note: S3 buckets won't be destroyed due to force_destroy=false
# RDS will create final snapshot due to skip_final_snapshot=false
```

3. **Manually Delete Protected Resources (If Needed):**
```bash
# If must delete S3 buckets (after confirming backups)
aws s3 rm s3://$(terraform output -raw s3_bucket_documents) --recursive
aws s3 rb s3://$(terraform output -raw s3_bucket_documents)

# If must delete RDS (after confirming snapshots)
aws rds delete-db-instance \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --final-db-snapshot-identifier final-emergency-$(date +%Y%m%d-%H%M%S)
```

4. **Document Shutdown:**
```bash
# Save infrastructure state before shutdown
terraform output -json > infrastructure-state-$(date +%Y%m%d-%H%M%S).json

# Save Git commit hash
git rev-parse HEAD > git-commit-$(date +%Y%m%d-%H%M%S).txt

# Save manual notes
cat > shutdown-notes-$(date +%Y%m%d-%H%M%S).txt << EOF
Shutdown Date: $(date)
Reason: [Emergency shutdown reason]
AWS Account: $(aws sts get-caller-identity --query Account --output text)
Terraform Workspace: $(terraform workspace show)
RDS Snapshot: emergency-shutdown-$(date +%Y%m%d-%H%M%S)
S3 Buckets: [List bucket names]
EOF
```

---

## Testing DR Procedures

### Quarterly DR Test Plan

**Test Schedule:** Every 3 months

**Test 1: RDS Snapshot Restore**
```bash
# 1. Create test database from production snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier hipaa-db-dr-test \
  --db-snapshot-identifier <latest-automated-snapshot> \
  --db-subnet-group-name dev-rds-subnet-group \
  --publicly-accessible false

# 2. Verify data accessibility
RDS_TEST_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-dr-test \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

psql -h $RDS_TEST_ENDPOINT -U admin_user -d hipaa_db -c "SELECT COUNT(*) FROM documents;"

# 3. Clean up test instance
aws rds delete-db-instance \
  --db-instance-identifier hipaa-db-dr-test \
  --skip-final-snapshot
```

**Test 2: S3 Object Recovery**
```bash
# 1. Delete test object
aws s3 rm s3://$(terraform output -raw s3_bucket_documents)/dr-test/test-file.txt

# 2. Restore from version history
aws s3api list-object-versions \
  --bucket $(terraform output -raw s3_bucket_documents) \
  --prefix dr-test/test-file.txt

aws s3api copy-object \
  --copy-source "$(terraform output -raw s3_bucket_documents)/dr-test/test-file.txt?versionId=<version-id>" \
  --bucket $(terraform output -raw s3_bucket_documents) \
  --key dr-test/test-file.txt

# 3. Verify restoration
aws s3 cp s3://$(terraform output -raw s3_bucket_documents)/dr-test/test-file.txt ./restored-test-file.txt
cat restored-test-file.txt
```

**Test 3: Terraform State Recovery**
```bash
# 1. Backup current state
cp .terraform/terraform.tfstate terraform.tfstate.backup-dr-test

# 2. Download previous version
aws s3api list-object-versions \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --prefix workspaces/dev/hipaa-infrastructure/terraform.tfstate \
  --query 'Versions[1].VersionId' --output text

aws s3api get-object \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --key workspaces/dev/hipaa-infrastructure/terraform.tfstate \
  --version-id <version-id> \
  terraform.tfstate.test

# 3. Verify state is valid
terraform show -json terraform.tfstate.test | jq .

# 4. Restore original state
cp terraform.tfstate.backup-dr-test .terraform/terraform.tfstate
```

---

## RTO and RPO Targets

### Current Capabilities

| Disaster Scenario | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) | Automation Level |
|-------------------|-------------------------------|-------------------------------|------------------|
| **RDS Data Loss (PITR)** | 15-30 minutes | 5 minutes | Manual |
| **RDS Data Loss (Snapshot)** | 15-30 minutes | Snapshot age | Manual |
| **RDS Instance Failure (Multi-AZ)** | 1-2 minutes | 0 (automatic failover) | Automatic |
| **RDS Instance Failure (Replica Promotion)** | 5-10 minutes | Replication lag (~seconds) | Manual |
| **S3 Object Deletion** | < 5 minutes | 0 (versioning) | Manual |
| **S3 Glacier Restore** | 3-5 hours | 0 (versioning) | Manual |
| **Terraform State Corruption** | < 5 minutes | Per state change | Manual |
| **Complete Infrastructure Rebuild** | 15-25 minutes | Terraform code | Manual |
| **Region Failure** | Not configured | N/A | N/A |

### Improvement Recommendations

**To Reduce RTO:**
1. **Automate Failover:** Implement Lambda functions to automatically promote read replicas on primary failure
2. **Cross-Region Replication:** Enable S3 cross-region replication for documents bucket
3. **Infrastructure as Code Automation:** Create scripts to automatically rebuild infrastructure from Terraform
4. **Monitoring and Alerting:** Implement CloudWatch alarms to detect failures faster

**To Reduce RPO:**
1. **Increase Backup Frequency:** RDS already at 5-minute PITR (maximum granularity)
2. **Real-Time Replication:** Multi-AZ and read replicas already provide real-time replication
3. **S3 Versioning:** Already enabled (0 RPO for S3)
4. **Application-Level Backups:** Export critical data to external storage daily

---

## Summary

**Key Takeaways:**
- RDS automated backups provide 5-minute RPO with 30-day retention
- S3 versioning enables immediate object recovery with 7-year retention
- Terraform state versioning in S3 enables infrastructure rollback
- Multi-AZ deployments provide automatic failover with minimal RTO
- Regular DR testing ensures procedures work when needed

**Monthly Checklist:**
- [ ] Verify RDS automated backups are running
- [ ] Verify S3 versioning is enabled on all buckets
- [ ] Test Terraform state recovery procedure
- [ ] Review and update DR documentation

**Quarterly Checklist:**
- [ ] Perform full RDS snapshot restore test
- [ ] Perform S3 object recovery test
- [ ] Perform read replica promotion test (production only)
- [ ] Update DR runbooks with lessons learned

**Annual Checklist:**
- [ ] Simulate complete infrastructure failure and rebuild
- [ ] Review and update RTO/RPO targets
- [ ] Audit disaster recovery procedures with stakeholders
- [ ] Evaluate cross-region disaster recovery implementation
