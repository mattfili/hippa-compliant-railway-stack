# Terraform Deployment Guide

Complete step-by-step guide for deploying AWS infrastructure for the HIPAA-compliant multi-tenant document management system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Environment-Specific Deployment](#environment-specific-deployment)
4. [Verification Steps](#verification-steps)
5. [Post-Deployment Configuration](#post-deployment-configuration)
6. [Common Deployment Scenarios](#common-deployment-scenarios)
7. [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Required Tools and Versions

| Tool | Minimum Version | Installation |
|------|----------------|--------------|
| Terraform CLI | 1.5.0+ | https://www.terraform.io/downloads |
| AWS CLI | 2.0+ | https://aws.amazon.com/cli/ |
| jq | 1.6+ | https://stedolan.github.io/jq/download/ |
| Git | 2.0+ | https://git-scm.com/downloads |

### AWS Account Requirements

- AWS account with administrative access
- IAM user with programmatic access (access key ID and secret access key)
- Service quotas sufficient for:
  - 1-3 VPCs (depending on environments)
  - 1-3 RDS instances (depending on environments)
  - 3-9 S3 buckets (3 per environment)
  - 3-9 KMS keys (3 per environment including per-tenant keys)
  - Multiple VPC subnets, NAT gateways, and elastic IPs

### Knowledge Requirements

- Basic understanding of AWS services (VPC, RDS, S3, IAM, KMS)
- Familiarity with Terraform syntax and workflows
- Understanding of HIPAA compliance requirements
- Knowledge of PostgreSQL database management

## Initial Setup

### Step 1: Configure AWS Credentials

Create or obtain AWS access credentials with administrative permissions.

#### Option A: Environment Variables

```bash
export AWS_ACCESS_KEY_ID="AKIAXXXXXXXXXXXXXXXX"
export AWS_SECRET_ACCESS_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export AWS_REGION="us-east-1"
```

#### Option B: AWS CLI Configuration

```bash
aws configure
# Enter Access Key ID, Secret Access Key, region (us-east-1), and output format (json)
```

#### Option C: AWS Profile

```bash
# Create named profile in ~/.aws/credentials
[hipaa-terraform]
aws_access_key_id = AKIAXXXXXXXXXXXXXXXX
aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
region = us-east-1

# Use profile in terraform commands
export AWS_PROFILE=hipaa-terraform
```

**Verify Credentials:**
```bash
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/terraform-admin"
}
```

### Step 2: Bootstrap Terraform State Backend

The Terraform state backend requires an S3 bucket and DynamoDB table. These must be created before running Terraform.

```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $AWS_ACCOUNT_ID"

# Create S3 bucket for Terraform state storage
aws s3api create-bucket \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --region us-east-1

# Enable versioning on state bucket (for rollback capability)
aws s3api put-bucket-versioning \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled

# Enable encryption on state bucket
aws s3api put-bucket-encryption \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access to state bucket
aws s3api put-public-access-block \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1 \
  --tags Key=Name,Value=terraform-state-lock Key=Environment,Value=shared Key=ManagedBy,Value=manual
```

**Verify Backend Resources:**
```bash
# Verify S3 bucket
aws s3 ls | grep terraform-state-hipaa

# Verify DynamoDB table
aws dynamodb describe-table --table-name terraform-state-lock --query 'Table.TableName'
```

### Step 3: Clone Repository and Initialize Terraform

```bash
# Clone repository
git clone <repository-url>
cd hippa-compliant-railway-stack

# Navigate to Terraform directory
cd terraform

# Initialize Terraform (download providers and configure backend)
terraform init \
  -backend-config="bucket=terraform-state-hipaa-${AWS_ACCOUNT_ID}" \
  -backend-config="region=us-east-1" \
  -backend-config="dynamodb_table=terraform-state-lock"
```

Expected output:
```
Initializing modules...
Initializing the backend...
Initializing provider plugins...
Terraform has been successfully initialized!
```

### Step 4: Create Terraform Workspaces

Workspaces provide environment isolation (dev, staging, production):

```bash
# Create development workspace
terraform workspace new dev

# Create staging workspace
terraform workspace new staging

# Create production workspace
terraform workspace new production

# List all workspaces
terraform workspace list
```

Expected output:
```
  default
* dev
  staging
  production
```

## Environment-Specific Deployment

### Development Environment Deployment

**Purpose:** Cost-optimized environment for development and testing.

**Characteristics:**
- Single-AZ RDS instance (db.t3.medium)
- 7-day backup retention
- No read replicas
- Deletion protection disabled
- Smaller storage allocations

**Estimated Monthly Cost:** $100-150

#### Deploy Development Environment

```bash
# Select development workspace
terraform workspace select dev

# Review configuration variables
cat terraform.tfvars.dev

# Format Terraform files (optional but recommended)
terraform fmt -recursive

# Validate configuration
terraform validate

# Plan infrastructure changes
terraform plan \
  -var-file="terraform.tfvars.dev" \
  -out=tfplan.dev

# Review the plan output carefully
# Verify:
# - Encryption enabled for RDS and S3
# - Security groups follow least-privilege
# - No public endpoints for RDS
# - Resource counts match expectations

# Apply infrastructure changes
terraform apply tfplan.dev
```

**Expected Provisioning Time:** 8-12 minutes

**Expected Resources Created:**
- 1 VPC with 6 subnets (3 public, 3 private)
- 3 NAT gateways (one per AZ)
- 1 Internet gateway
- 3 VPC endpoints (S3, RDS, Bedrock)
- 3 security groups (RDS, app, VPC endpoints)
- 1 RDS PostgreSQL instance (db.t3.medium, single-AZ)
- 3 S3 buckets (documents, backups, audit-logs)
- 1 KMS key (master infrastructure key)
- 1 IAM role with 3 policies (S3, KMS, Bedrock)
- 1 AWS Config recorder with 6+ rules
- 1 SNS topic (for Config alerts)

#### Export Development Outputs

```bash
# Export outputs to JSON for Railway integration
terraform output -json > outputs.json

# View specific outputs
terraform output rds_endpoint
terraform output s3_bucket_documents
terraform output kms_master_key_id

# Store outputs securely for Railway environment variables
cat outputs.json
```

### Staging Environment Deployment

**Purpose:** Production-like environment for pre-production validation.

**Characteristics:**
- Multi-AZ RDS instance (db.t3.large)
- 30-day backup retention
- No read replicas
- Deletion protection disabled
- Medium storage allocations

**Estimated Monthly Cost:** $250-350

#### Deploy Staging Environment

```bash
# Select staging workspace
terraform workspace select staging

# Plan infrastructure changes
terraform plan \
  -var-file="terraform.tfvars.staging" \
  -out=tfplan.staging

# Review plan output
# Verify Multi-AZ configuration enabled

# Apply infrastructure changes
terraform apply tfplan.staging

# Export outputs
terraform output -json > outputs.staging.json
```

**Expected Provisioning Time:** 12-15 minutes (Multi-AZ takes longer)

### Production Environment Deployment

**Purpose:** High-availability production environment for customer data.

**Characteristics:**
- Multi-AZ RDS instance (db.r6g.xlarge)
- Read replica enabled
- 30-day backup retention
- Deletion protection enabled
- Large storage allocations
- Performance Insights enabled

**Estimated Monthly Cost:** $500-800 (without reserved instances)

#### Deploy Production Environment

**WARNING:** Production deployment requires additional caution. Review all steps carefully.

```bash
# Select production workspace
terraform workspace select production

# Plan infrastructure changes
terraform plan \
  -var-file="terraform.tfvars.production" \
  -out=tfplan.production

# Review plan output extensively
# Verify:
# - Multi-AZ enabled
# - Read replica enabled
# - Deletion protection enabled
# - Backup retention set to 30 days
# - Performance Insights enabled
# - All encryption enabled

# Create manual pre-deployment snapshot (if updating existing infrastructure)
aws rds create-db-snapshot \
  --db-instance-identifier hipaa-db-production \
  --db-snapshot-identifier manual-pre-deployment-$(date +%Y%m%d-%H%M%S)

# Apply infrastructure changes
terraform apply tfplan.production

# Export outputs
terraform output -json > outputs.production.json
```

**Expected Provisioning Time:** 15-20 minutes (Multi-AZ + read replica)

## Verification Steps

### Step 1: Verify RDS Connectivity

```bash
# Get RDS endpoint from outputs
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
echo "RDS Endpoint: $RDS_ENDPOINT"

# Extract host and port
RDS_HOST=$(echo $RDS_ENDPOINT | cut -d: -f1)
RDS_PORT=$(echo $RDS_ENDPOINT | cut -d: -f2)

# Test connectivity from local machine (requires network access)
# Note: RDS is in private subnet, so this requires VPN or bastion host
nc -zv $RDS_HOST $RDS_PORT

# Alternative: Test from AWS Console RDS Query Editor
# Or deploy a test EC2 instance in the same VPC
```

### Step 2: Verify S3 Bucket Encryption

```bash
# Get bucket name from outputs
S3_BUCKET_DOCUMENTS=$(terraform output -raw s3_bucket_documents)

# Verify encryption configuration
aws s3api get-bucket-encryption \
  --bucket $S3_BUCKET_DOCUMENTS

# Expected output: SSE-KMS with KMS key ARN

# Verify versioning enabled
aws s3api get-bucket-versioning \
  --bucket $S3_BUCKET_DOCUMENTS

# Expected output: Status=Enabled

# Verify public access blocked
aws s3api get-public-access-block \
  --bucket $S3_BUCKET_DOCUMENTS

# Expected output: All settings = true
```

### Step 3: Verify KMS Key Rotation

```bash
# Get KMS key ID from outputs
KMS_KEY_ID=$(terraform output -raw kms_master_key_id)

# Check key rotation status
aws kms get-key-rotation-status \
  --key-id $KMS_KEY_ID

# Expected output: KeyRotationEnabled=true

# Describe key details
aws kms describe-key \
  --key-id $KMS_KEY_ID
```

### Step 4: Verify Security Group Rules

```bash
# List security groups in VPC
VPC_ID=$(terraform output -raw vpc_id)

aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'SecurityGroups[*].[GroupId,GroupName,IpPermissions]' \
  --output table

# Verify:
# - RDS security group allows only port 5432 from app security group
# - No 0.0.0.0/0 rules on sensitive ports
# - App security group allows only HTTPS inbound
```

### Step 5: Verify AWS Config Rules

```bash
# Check Config recorder status
aws configservice describe-configuration-recorder-status

# Expected output: recording=true

# List Config rules
aws configservice describe-config-rules \
  --query 'ConfigRules[*].[ConfigRuleName,ConfigRuleState]' \
  --output table

# Verify at least 6 rules are ACTIVE

# Check compliance status
aws configservice describe-compliance-by-config-rule \
  --query 'ComplianceByConfigRules[*].[ConfigRuleName,Compliance.ComplianceType]' \
  --output table
```

### Step 6: Verify Application Health

If deploying with Railway integration:

```bash
# Application should start with loaded environment variables
# Check Railway logs for:
# - "Terraform outputs loaded successfully"
# - "Database migrations completed successfully"
# - "Application server started"

# Test health endpoint
curl https://your-railway-domain.railway.app/api/v1/health/ready

# Expected response: 200 OK with JSON status
```

## Post-Deployment Configuration

### Step 1: Store RDS Password in AWS Secrets Manager

The RDS password is generated by Terraform but should be stored securely:

```bash
# Get the RDS username
RDS_USERNAME=$(terraform output -raw rds_username)

# Store password in Secrets Manager (replace with actual password)
aws secretsmanager create-secret \
  --name hipaa-rds-password-$(terraform workspace show) \
  --description "RDS master password for $(terraform workspace show) environment" \
  --secret-string '{"username":"'$RDS_USERNAME'","password":"CHANGE_ME_SECURE_PASSWORD"}'

# Update Railway environment variables with secret ARN
SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id hipaa-rds-password-$(terraform workspace show) \
  --query ARN --output text)

echo "Set Railway environment variable: AWS_SECRETS_MANAGER_SECRET_ID=$SECRET_ARN"
```

### Step 2: Configure Railway Environment Variables

Set the following environment variables in Railway:

**User-Provided Variables:**
```bash
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
ENVIRONMENT=production  # or dev, staging
RDS_PASSWORD=<secure-password>
OIDC_ISSUER_URL=<your-cognito-or-auth0-url>
OIDC_CLIENT_ID=<your-client-id>
OIDC_CLIENT_SECRET=<your-client-secret>
```

**Auto-Generated Variables** (from Terraform outputs via startup script):
- DATABASE_URL
- S3_BUCKET_DOCUMENTS
- S3_BUCKET_BACKUPS
- S3_BUCKET_AUDIT_LOGS
- KMS_MASTER_KEY_ID
- KMS_MASTER_KEY_ARN
- VPC_ID
- APP_IAM_ROLE_ARN

### Step 3: Create First Tenant

After application deployment, create the first tenant:

```bash
# Get JWT token (authenticate as admin user)
JWT_TOKEN="<your-jwt-token>"

# Create first tenant
curl -X POST https://your-railway-domain.railway.app/api/v1/tenants \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Healthcare",
    "slug": "acme-healthcare"
  }'

# Verify per-tenant KMS key created
aws kms list-keys --query 'Keys[?contains(KeyId, `tenant`)]'
```

### Step 4: Enable CloudTrail Logging (Optional)

For enhanced audit logging:

```bash
# Create CloudTrail trail
aws cloudtrail create-trail \
  --name hipaa-audit-trail-$(terraform workspace show) \
  --s3-bucket-name $(terraform output -raw s3_bucket_audit_logs) \
  --is-multi-region-trail \
  --enable-log-file-validation

# Start logging
aws cloudtrail start-logging \
  --name hipaa-audit-trail-$(terraform workspace show)
```

## Common Deployment Scenarios

### Scenario 1: Update Infrastructure (e.g., scale RDS)

```bash
# Select workspace
terraform workspace select production

# Edit terraform.tfvars.production
# Change: rds_instance_class = "db.r6g.2xlarge"

# Create manual snapshot before changes
aws rds create-db-snapshot \
  --db-instance-identifier hipaa-db-production \
  --db-snapshot-identifier manual-pre-scale-$(date +%Y%m%d-%H%M%S)

# Plan changes
terraform plan -var-file="terraform.tfvars.production" -out=tfplan

# Apply changes (this will cause RDS downtime for instance class change)
terraform apply tfplan

# Verify new instance class
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-production \
  --query 'DBInstances[0].DBInstanceClass'
```

### Scenario 2: Add New S3 Bucket

```bash
# Edit modules/s3/main.tf to add new bucket resource

# Plan changes
terraform plan -var-file="terraform.tfvars.dev" -out=tfplan

# Apply changes (no downtime)
terraform apply tfplan

# Update outputs.tf to export new bucket name
# Re-apply to update outputs
terraform apply -var-file="terraform.tfvars.dev"
```

### Scenario 3: Rotate KMS Keys

```bash
# KMS key rotation is automatic (enabled by default)
# To manually rotate immediately:

KMS_KEY_ID=$(terraform output -raw kms_master_key_id)

aws kms enable-key-rotation --key-id $KMS_KEY_ID

# Verify rotation enabled
aws kms get-key-rotation-status --key-id $KMS_KEY_ID

# Note: Rotation happens annually, existing encrypted data remains accessible
```

### Scenario 4: Add New Config Rule

```bash
# Edit modules/config/main.tf to add new aws_config_config_rule

# Example: Add encryption check for EBS volumes
resource "aws_config_config_rule" "ebs_encrypted" {
  name = "${var.environment}-ebs-encrypted-volumes"

  source {
    owner             = "AWS"
    source_identifier = "ENCRYPTED_VOLUMES"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

# Apply changes
terraform plan -var-file="terraform.tfvars.production" -out=tfplan
terraform apply tfplan

# Verify new rule active
aws configservice describe-config-rules \
  --config-rule-names production-ebs-encrypted-volumes
```

## Rollback Procedures

See the detailed [Disaster Recovery Documentation](./TERRAFORM_DISASTER_RECOVERY.md) for comprehensive rollback procedures.

### Quick Rollback: Terraform State

```bash
# List state versions
aws s3api list-object-versions \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --prefix workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate \
  --query 'Versions[*].[VersionId,LastModified]' \
  --output table

# Download previous state version
aws s3api get-object \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --key workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate \
  --version-id <version-id> \
  terraform.tfstate.rollback

# Backup current state
cp .terraform/terraform.tfstate terraform.tfstate.current

# Replace with previous state
cp terraform.tfstate.rollback .terraform/terraform.tfstate

# Verify state
terraform show

# Apply previous configuration
terraform apply -var-file="terraform.tfvars.$(terraform workspace show)"
```

### Quick Rollback: RDS Snapshot

```bash
# List available snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]' \
  --output table

# Restore from snapshot (creates new instance)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier hipaa-db-$(terraform workspace show)-restored \
  --db-snapshot-identifier manual-snapshot-20251017-120000

# Update Terraform to manage restored instance
terraform import module.rds.aws_db_instance.main hipaa-db-$(terraform workspace show)-restored

# Or: Update connection strings to point to restored instance
```

## Troubleshooting

### Issue: Terraform Init Fails

**Error:** `Error: Failed to get existing workspaces`

**Solution:**
```bash
# Verify backend configuration
cat backend.tf

# Verify AWS credentials
aws sts get-caller-identity

# Verify S3 bucket exists
aws s3 ls | grep terraform-state-hipaa

# Re-initialize with explicit backend config
terraform init -reconfigure \
  -backend-config="bucket=terraform-state-hipaa-${AWS_ACCOUNT_ID}"
```

### Issue: RDS Provisioning Timeout

**Error:** `Error: timeout while waiting for state to become 'available'`

**Solution:**
```bash
# RDS provisioning can take 10-20 minutes
# Increase timeout in modules/rds/main.tf:

resource "aws_db_instance" "main" {
  # Add timeout
  timeouts {
    create = "60m"
    update = "80m"
    delete = "60m"
  }
}

# Check RDS status manually
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --query 'DBInstances[0].DBInstanceStatus'

# If status is "creating" or "backing-up", wait and retry
terraform apply -var-file="terraform.tfvars.$(terraform workspace show)"
```

### Issue: State Lock Error

**Error:** `Error: Error acquiring the state lock`

**Solution:**
```bash
# Check who holds the lock
aws dynamodb get-item \
  --table-name terraform-state-lock \
  --key '{"LockID":{"S":"terraform-state-hipaa-'${AWS_ACCOUNT_ID}'/workspaces/'$(terraform workspace show)'/hipaa-infrastructure/terraform.tfstate-md5"}}'

# If lock is stale (operation crashed), force unlock
terraform force-unlock <lock-id>

# WARNING: Only force unlock if you're certain no other terraform process is running
```

### Issue: Resource Already Exists

**Error:** `Error: Resource already exists`

**Solution:**
```bash
# Import existing resource into Terraform state
# Example: Import VPC
terraform import module.vpc.aws_vpc.main vpc-xxxxx

# Example: Import RDS instance
terraform import module.rds.aws_db_instance.main hipaa-db-dev

# After import, run plan to verify state matches configuration
terraform plan -var-file="terraform.tfvars.dev"
```

### Issue: Insufficient Permissions

**Error:** `Error: UnauthorizedOperation: You are not authorized to perform this operation`

**Solution:**
```bash
# Verify IAM user/role has required permissions
aws iam get-user-policy \
  --user-name terraform-admin \
  --policy-name AdministratorAccess

# Attach Administrator Access policy (or more restrictive custom policy)
aws iam attach-user-policy \
  --user-name terraform-admin \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Or create least-privilege policy for Terraform operations
```

## Best Practices

### Before Deployment
1. **Review Plan Output:** Always review `terraform plan` output before applying
2. **Create Manual Snapshots:** Create RDS snapshots before destructive changes
3. **Test in Dev First:** Test changes in dev environment before staging/production
4. **Validate Configuration:** Run `terraform validate` and `terraform fmt -check`

### During Deployment
1. **Monitor Progress:** Watch AWS Console for resource creation status
2. **Save Plan Files:** Use `-out` flag to save plan and apply the saved plan
3. **Document Changes:** Note what changes are being made and why
4. **Monitor Costs:** Check AWS Cost Explorer after deployment

### After Deployment
1. **Verify Resources:** Run verification steps to ensure resources are configured correctly
2. **Test Connectivity:** Verify application can connect to RDS and S3
3. **Check Compliance:** Verify AWS Config rules are active and passing
4. **Update Documentation:** Document any deviations from standard configuration

### Ongoing Operations
1. **Regular Updates:** Keep Terraform and provider versions up to date
2. **State Backups:** Regularly backup Terraform state files
3. **Cost Monitoring:** Review monthly costs and optimize as needed
4. **Security Audits:** Regularly review security group rules and IAM policies

## Additional Resources

- [Terraform Troubleshooting Guide](./TERRAFORM_TROUBLESHOOTING.md)
- [Disaster Recovery Procedures](./TERRAFORM_DISASTER_RECOVERY.md)
- [HIPAA Compliance Mapping](./HIPAA_COMPLIANCE_MAPPING.md)
- [Cost Optimization Strategies](./TERRAFORM_COST_OPTIMIZATION.md)
- [Operations Runbook](./TERRAFORM_OPERATIONS_RUNBOOK.md)
- [Multi-Environment Strategy](./TERRAFORM_MULTI_ENVIRONMENT_STRATEGY.md)
- [Railway Integration Guide](./TERRAFORM_RAILWAY_INTEGRATION.md)

## Support

For deployment issues:
1. Check troubleshooting guide above
2. Review Terraform documentation: https://www.terraform.io/docs
3. Review AWS documentation: https://docs.aws.amazon.com
4. Check module-specific README files in `terraform/modules/`
5. Contact DevOps team or infrastructure administrator
