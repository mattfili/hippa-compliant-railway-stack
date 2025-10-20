# Terraform Troubleshooting Guide

Comprehensive troubleshooting guide for common issues encountered when deploying and managing AWS infrastructure with Terraform.

## Table of Contents

1. [Terraform Initialization Issues](#terraform-initialization-issues)
2. [State Management Issues](#state-management-issues)
3. [Resource Provisioning Issues](#resource-provisioning-issues)
4. [Networking and Connectivity Issues](#networking-and-connectivity-issues)
5. [Security and Permissions Issues](#security-and-permissions-issues)
6. [Module-Specific Issues](#module-specific-issues)
7. [Debugging Techniques](#debugging-techniques)
8. [State Corruption Recovery](#state-corruption-recovery)
9. [Resource Import Procedures](#resource-import-procedures)

## Terraform Initialization Issues

### Error: Backend Initialization Required

**Symptoms:**
```
Error: Backend initialization required, please run "terraform init"
```

**Cause:** Terraform backend configuration changed or providers need to be downloaded.

**Solution:**
```bash
# Re-initialize Terraform
cd terraform
terraform init

# If backend config changed, use -reconfigure
terraform init -reconfigure

# If migrating state, use -migrate-state
terraform init -migrate-state
```

### Error: Failed to Get Existing Workspaces

**Symptoms:**
```
Error: Failed to get existing workspaces: NoSuchBucket: The specified bucket does not exist
```

**Cause:** S3 backend bucket doesn't exist or incorrect bucket name in backend configuration.

**Solution:**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check if bucket exists
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 ls | grep terraform-state-hipaa

# If bucket doesn't exist, create it
aws s3api create-bucket \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled

# Re-initialize
terraform init
```

### Error: Incompatible Provider Version

**Symptoms:**
```
Error: Incompatible provider version
Provider registry.terraform.io/hashicorp/aws v4.x.x does not have a package available
```

**Cause:** Provider version constraint in `versions.tf` not compatible with local Terraform version.

**Solution:**
```bash
# Check Terraform version
terraform version

# Update versions.tf to use compatible provider version
# Edit: required_providers.aws.version = ">= 5.0"

# Remove lock file and re-initialize
rm .terraform.lock.hcl
terraform init

# Or upgrade providers
terraform init -upgrade
```

### Error: Plugin Did Not Respond

**Symptoms:**
```
Error: Plugin did not respond
```

**Cause:** Terraform provider crashed or network timeout during download.

**Solution:**
```bash
# Clear provider cache
rm -rf .terraform
rm .terraform.lock.hcl

# Re-initialize with debug logging
export TF_LOG=DEBUG
terraform init

# Check network connectivity
curl -I https://registry.terraform.io

# If behind proxy, set HTTP_PROXY and HTTPS_PROXY env vars
export HTTPS_PROXY=http://proxy.company.com:8080
terraform init
```

## State Management Issues

### Error: State Lock Acquisition Failed

**Symptoms:**
```
Error: Error acquiring the state lock

Lock Info:
  ID:        a1b2c3d4-5678-90ab-cdef-1234567890ab
  Path:      terraform-state-hipaa-123456789012/workspaces/dev/hipaa-infrastructure/terraform.tfstate
  Operation: OperationTypeApply
  Who:       user@hostname
  Version:   1.5.0
  Created:   2025-10-17 10:30:00.000000 UTC
```

**Cause:** Another Terraform process is running, or previous process crashed without releasing lock.

**Solution:**
```bash
# 1. Verify no other terraform processes are running
ps aux | grep terraform

# 2. Check lock in DynamoDB
aws dynamodb get-item \
  --table-name terraform-state-lock \
  --key '{"LockID":{"S":"terraform-state-hipaa-'${AWS_ACCOUNT_ID}'/workspaces/'$(terraform workspace show)'/hipaa-infrastructure/terraform.tfstate-md5"}}'

# 3. If lock is stale (operation crashed), force unlock
# WARNING: Only do this if you're certain no other process is running
terraform force-unlock a1b2c3d4-5678-90ab-cdef-1234567890ab

# 4. Retry operation
terraform apply -var-file="terraform.tfvars.dev"
```

### Error: State File Version Too New

**Symptoms:**
```
Error: state snapshot was created by Terraform v1.5.0, which is newer than current v1.4.0
```

**Cause:** State file was written by a newer version of Terraform.

**Solution:**
```bash
# Option 1: Upgrade Terraform to match or exceed state version
# Download from https://www.terraform.io/downloads

# Option 2: Restore previous state version (if available)
aws s3api list-object-versions \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --prefix workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate

# Download older version
aws s3api get-object \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --key workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate \
  --version-id <older-version-id> \
  terraform.tfstate.older

# Replace current state (BACKUP FIRST!)
cp .terraform/terraform.tfstate terraform.tfstate.backup
cp terraform.tfstate.older .terraform/terraform.tfstate
```

### Error: State File Corruption

**Symptoms:**
```
Error: Failed to load state: EOF
```

**Cause:** State file is corrupted or incomplete.

**Solution:**
```bash
# 1. Backup current state
cp .terraform/terraform.tfstate terraform.tfstate.corrupted

# 2. Try to recover state from S3
aws s3 cp \
  s3://terraform-state-hipaa-${AWS_ACCOUNT_ID}/workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate \
  terraform.tfstate.recovered

# 3. Verify recovered state
terraform show -json terraform.tfstate.recovered | jq .

# 4. If valid, replace corrupted state
cp terraform.tfstate.recovered .terraform/terraform.tfstate

# 5. Refresh state
terraform refresh -var-file="terraform.tfvars.$(terraform workspace show)"

# 6. If state unrecoverable, restore from previous version (see State File Version section above)
```

## Resource Provisioning Issues

### Error: RDS Instance Creation Timeout

**Symptoms:**
```
Error: timeout while waiting for state to become 'available' (last state: 'backing-up', timeout: 40m0s)
```

**Cause:** RDS instance creation takes longer than default timeout, especially for Multi-AZ deployments.

**Solution:**
```bash
# 1. Check RDS instance status manually
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --query 'DBInstances[0].[DBInstanceIdentifier,DBInstanceStatus,MultiAZ]' \
  --output table

# 2. If status is "creating" or "backing-up", wait 5-10 minutes and retry
# RDS provisioning can take 15-20 minutes for Multi-AZ

# 3. Increase timeout in modules/rds/main.tf
# Add to aws_db_instance resource:
timeouts {
  create = "60m"
  update = "80m"
  delete = "60m"
}

# 4. Re-apply (Terraform will continue where it left off)
terraform apply -var-file="terraform.tfvars.$(terraform workspace show)"

# 5. If instance exists but Terraform doesn't recognize it, import it
terraform import module.rds.aws_db_instance.main hipaa-db-$(terraform workspace show)
```

### Error: VPC CIDR Block Already Exists

**Symptoms:**
```
Error: error creating VPC: VpcLimitExceeded: The maximum number of VPCs has been reached
```

**Cause:** AWS account VPC limit reached (default: 5 VPCs per region).

**Solution:**
```bash
# 1. List existing VPCs
aws ec2 describe-vpcs \
  --query 'Vpcs[*].[VpcId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# 2. Delete unused VPCs
aws ec2 delete-vpc --vpc-id vpc-xxxxx

# 3. Or request VPC limit increase
aws service-quotas get-service-quota \
  --service-code vpc \
  --quota-code L-F678F1CE

# Request increase to 10 VPCs
aws service-quotas request-service-quota-increase \
  --service-code vpc \
  --quota-code L-F678F1CE \
  --desired-value 10
```

### Error: S3 Bucket Already Exists

**Symptoms:**
```
Error: error creating S3 Bucket: BucketAlreadyExists: The requested bucket name is not available
```

**Cause:** S3 bucket names are globally unique across all AWS accounts.

**Solution:**
```bash
# 1. Check if bucket exists in your account
aws s3 ls | grep hipaa-compliant

# 2. If bucket exists and is yours, import it
terraform import module.s3.aws_s3_bucket.documents hipaa-compliant-docs-dev-123456789012

# 3. If bucket name is taken by another account, change bucket name
# Edit terraform.tfvars.dev:
documents_bucket_name = "hipaa-compliant-docs-dev-${random_suffix}"

# 4. Or use account ID in bucket name (already done in modules/s3)
# Verify account ID is correct
aws sts get-caller-identity --query Account --output text
```

### Error: KMS Key Pending Deletion

**Symptoms:**
```
Error: error creating KMS Key: InvalidStateException: KMS key is pending deletion
```

**Cause:** KMS key with same alias was previously scheduled for deletion.

**Solution:**
```bash
# 1. List KMS keys and find key pending deletion
aws kms list-keys --query 'Keys[*].KeyId' --output text | \
  xargs -I {} aws kms describe-key --key-id {} --query 'KeyMetadata.[KeyId,KeyState,DeletionDate]' --output text

# 2. Cancel deletion if within 30-day window
aws kms cancel-key-deletion --key-id <key-id>

# 3. Re-enable key
aws kms enable-key --key-id <key-id>

# 4. Import key into Terraform state
terraform import module.kms.aws_kms_key.master <key-id>

# 5. Or wait for deletion to complete (up to 30 days) and create new key
```

## Networking and Connectivity Issues

### Error: Cannot Connect to RDS from Application

**Symptoms:**
- Application logs show: `could not connect to server: Connection timed out`
- Health check fails

**Cause:** Security group rules, network ACLs, or VPC routing misconfigured.

**Solution:**
```bash
# 1. Verify RDS is in private subnet
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --query 'DBInstances[0].[DBSubnetGroup.Subnets[*].SubnetIdentifier,PubliclyAccessible]' \
  --output table

# PubliclyAccessible should be false

# 2. Verify security group rules
RDS_SG=$(aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
  --output text)

aws ec2 describe-security-groups --group-ids $RDS_SG

# Should allow port 5432 from app security group

# 3. Test connectivity from within VPC (launch EC2 instance in same VPC)
# Or use Railway logs to check if environment variables are loaded

# 4. Verify VPC endpoint for RDS is working (if used)
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.us-east-1.rds" \
  --query 'VpcEndpoints[*].[VpcEndpointId,State,VpcId]' \
  --output table

# 5. Check Railway environment variable mapping
# Verify DATABASE_URL is constructed correctly in startup script
```

### Error: NAT Gateway Not Routing Traffic

**Symptoms:**
- Private subnets cannot reach internet
- RDS cannot download updates

**Cause:** Route table not associated with NAT gateway or NAT gateway in wrong subnet.

**Solution:**
```bash
# 1. List NAT gateways and verify they're in public subnets
VPC_ID=$(terraform output -raw vpc_id)
aws ec2 describe-nat-gateways \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query 'NatGateways[*].[NatGatewayId,SubnetId,State]' \
  --output table

# 2. Verify route tables for private subnets
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[*].[RouteTableId,Associations[*].SubnetId,Routes[*].[DestinationCidrBlock,NatGatewayId]]' \
  --output json | jq .

# 3. Verify default route (0.0.0.0/0) points to NAT gateway for private subnets

# 4. Check NAT gateway has Elastic IP
aws ec2 describe-nat-gateways \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query 'NatGateways[*].[NatGatewayId,NatGatewayAddresses[0].PublicIp]' \
  --output table

# 5. If issues persist, recreate NAT gateway
terraform taint module.vpc.aws_nat_gateway.main[0]
terraform apply -var-file="terraform.tfvars.$(terraform workspace show)"
```

### Error: VPC Endpoint Not Accessible

**Symptoms:**
- S3 operations timeout or fail
- High NAT gateway data transfer costs

**Cause:** VPC endpoint not associated with correct route tables or security groups.

**Solution:**
```bash
# 1. Verify S3 gateway endpoint exists and is available
VPC_ID=$(terraform output -raw vpc_id)
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=service-name,Values=com.amazonaws.us-east-1.s3" \
  --query 'VpcEndpoints[*].[VpcEndpointId,State,RouteTableIds]' \
  --output table

# State should be "available"

# 2. Verify route tables are associated with VPC endpoint
aws ec2 describe-route-tables \
  --route-table-ids $(aws ec2 describe-vpc-endpoints \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=service-name,Values=com.amazonaws.us-east-1.s3" \
    --query 'VpcEndpoints[0].RouteTableIds[*]' --output text)

# 3. For interface endpoints (RDS, Bedrock), verify security group allows HTTPS (443)
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=service-name,Values=com.amazonaws.us-east-1.bedrock-runtime" \
  --query 'VpcEndpoints[*].[VpcEndpointId,Groups[*].GroupId]' \
  --output table

# 4. Test S3 access from within VPC
# From EC2 instance or Lambda:
aws s3 ls s3://$(terraform output -raw s3_bucket_documents)
```

## Security and Permissions Issues

### Error: UnauthorizedOperation

**Symptoms:**
```
Error: UnauthorizedOperation: You are not authorized to perform this operation
```

**Cause:** IAM user or role lacks required permissions for Terraform operations.

**Solution:**
```bash
# 1. Verify current IAM identity
aws sts get-caller-identity

# 2. Check attached policies
aws iam list-attached-user-policies --user-name terraform-admin

# 3. Attach AdministratorAccess policy (or custom policy)
aws iam attach-user-policy \
  --user-name terraform-admin \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# 4. Or create least-privilege policy for Terraform
# Required permissions:
# - ec2:* (VPC, subnets, security groups)
# - rds:* (RDS instances)
# - s3:* (S3 buckets)
# - kms:* (KMS keys)
# - iam:* (IAM roles and policies)
# - config:* (AWS Config)
# - sns:* (SNS topics)
# - dynamodb:* (for state locking)

# 5. Verify permissions
aws iam simulate-principal-policy \
  --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
  --action-names ec2:CreateVpc rds:CreateDBInstance s3:CreateBucket
```

### Error: Access Denied to S3 Bucket

**Symptoms:**
```
Error: error reading S3 Bucket: AccessDenied: Access Denied
```

**Cause:** S3 bucket policy or IAM policy blocks access.

**Solution:**
```bash
# 1. Check bucket policy
aws s3api get-bucket-policy \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID}

# 2. Check bucket ACL
aws s3api get-bucket-acl \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID}

# 3. Verify IAM permissions
aws iam get-user-policy \
  --user-name terraform-admin \
  --policy-name S3FullAccess

# 4. Add bucket policy allowing Terraform user
aws s3api put-bucket-policy \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::'${AWS_ACCOUNT_ID}':user/terraform-admin"
      },
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::terraform-state-hipaa-'${AWS_ACCOUNT_ID}'",
        "arn:aws:s3:::terraform-state-hipaa-'${AWS_ACCOUNT_ID}'/*"
      ]
    }]
  }'
```

### Error: KMS Access Denied

**Symptoms:**
```
Error: error encrypting S3 object: AccessDenied: User is not authorized to perform: kms:GenerateDataKey
```

**Cause:** IAM user or role not granted permissions in KMS key policy.

**Solution:**
```bash
# 1. Get KMS key ID
KMS_KEY_ID=$(terraform output -raw kms_master_key_id)

# 2. Check key policy
aws kms get-key-policy \
  --key-id $KMS_KEY_ID \
  --policy-name default

# 3. Update key policy to allow Terraform user
# Edit modules/kms/main.tf key policy to include:
{
  "Sid": "Allow Terraform user",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::${var.aws_account_id}:user/terraform-admin"
  },
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:GenerateDataKey",
    "kms:DescribeKey"
  ],
  "Resource": "*"
}

# 4. Re-apply Terraform
terraform apply -var-file="terraform.tfvars.$(terraform workspace show)"
```

## Module-Specific Issues

### VPC Module: Subnet CIDR Conflicts

**Symptoms:**
```
Error: error creating subnet: InvalidSubnet.Conflict: The CIDR '10.0.1.0/24' conflicts with another subnet
```

**Cause:** Subnet CIDR blocks overlap or conflict with existing subnets.

**Solution:**
```bash
# 1. List existing subnets in VPC
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone]' \
  --output table

# 2. Adjust CIDR blocks in modules/vpc/main.tf
# Ensure no overlaps and CIDRs fit within VPC CIDR

# 3. Or delete conflicting subnets (if safe)
aws ec2 delete-subnet --subnet-id subnet-xxxxx
```

### RDS Module: Parameter Group Changes Require Reboot

**Symptoms:**
```
Warning: RDS instance requires reboot to apply parameter changes
```

**Cause:** Some parameter group changes require RDS instance reboot.

**Solution:**
```bash
# 1. Check pending modifications
aws rds describe-db-instances \
  --db-instance-identifier hipaa-db-$(terraform workspace show) \
  --query 'DBInstances[0].PendingModifiedValues'

# 2. Schedule reboot during maintenance window
aws rds reboot-db-instance \
  --db-instance-identifier hipaa-db-$(terraform workspace show)

# 3. Or let RDS reboot during next maintenance window
# (check maintenance window in terraform output or AWS Console)
```

### S3 Module: Lifecycle Policy Not Working

**Symptoms:**
- Objects not transitioning to STANDARD_IA or Glacier
- No cost savings observed

**Cause:** Lifecycle policies take time to evaluate or objects don't meet criteria.

**Solution:**
```bash
# 1. Verify lifecycle policy exists
S3_BUCKET_DOCUMENTS=$(terraform output -raw s3_bucket_documents)
aws s3api get-bucket-lifecycle-configuration \
  --bucket $S3_BUCKET_DOCUMENTS

# 2. Check object age
aws s3api list-objects-v2 \
  --bucket $S3_BUCKET_DOCUMENTS \
  --query 'Contents[*].[Key,LastModified,StorageClass]' \
  --output table

# 3. Lifecycle policies evaluate daily
# Objects transition within 24-48 hours of meeting criteria

# 4. Test with smaller transition period
# Edit modules/s3/main.tf:
transition {
  days          = 1  # Test with 1 day instead of 90
  storage_class = "STANDARD_IA"
}
```

### IAM Module: Policy Too Large

**Symptoms:**
```
Error: error creating IAM Policy: LimitExceeded: Cannot exceed quota for PolicySize
```

**Cause:** IAM policy exceeds 6,144 characters (managed policy limit).

**Solution:**
```bash
# 1. Split large policy into multiple smaller policies
# Edit modules/iam/main.tf:

# Original:
resource "aws_iam_policy" "s3_kms_bedrock" {
  # All permissions in one policy
}

# Split:
resource "aws_iam_policy" "s3_access" {
  # Only S3 permissions
}

resource "aws_iam_policy" "kms_access" {
  # Only KMS permissions
}

resource "aws_iam_policy" "bedrock_access" {
  # Only Bedrock permissions
}

# 2. Attach all policies to role
resource "aws_iam_role_policy_attachment" "s3" {
  role       = aws_iam_role.backend_app.name
  policy_arn = aws_iam_policy.s3_access.arn
}

resource "aws_iam_role_policy_attachment" "kms" {
  role       = aws_iam_role.backend_app.name
  policy_arn = aws_iam_policy.kms_access.arn
}

resource "aws_iam_role_policy_attachment" "bedrock" {
  role       = aws_iam_role.backend_app.name
  policy_arn = aws_iam_policy.bedrock_access.arn
}

# 3. Re-apply
terraform apply -var-file="terraform.tfvars.$(terraform workspace show)"
```

### Config Module: Rules Not Evaluating

**Symptoms:**
- Config rules show "No resources in scope"
- Compliance status not updating

**Cause:** Config recorder not started or resources not in scope.

**Solution:**
```bash
# 1. Verify Config recorder is recording
aws configservice describe-configuration-recorder-status

# Should show: recording=true

# 2. Start recorder if stopped
aws configservice start-configuration-recorder \
  --configuration-recorder-name $(terraform workspace show)-config-recorder

# 3. Verify resources are being recorded
aws configservice list-discovered-resources \
  --resource-type AWS::S3::Bucket

# 4. Manually trigger rule evaluation
aws configservice start-config-rules-evaluation \
  --config-rule-names $(terraform workspace show)-s3-bucket-encryption-enabled

# 5. Check compliance status
aws configservice describe-compliance-by-config-rule \
  --config-rule-names $(terraform workspace show)-s3-bucket-encryption-enabled
```

## Debugging Techniques

### Enable Terraform Debug Logging

```bash
# Set log level (TRACE, DEBUG, INFO, WARN, ERROR)
export TF_LOG=DEBUG

# Write logs to file
export TF_LOG_PATH=./terraform-debug.log

# Run Terraform command
terraform apply -var-file="terraform.tfvars.dev"

# Review logs
cat terraform-debug.log | grep ERROR
```

### Inspect Terraform State

```bash
# Show entire state
terraform show

# Show specific resource
terraform state show module.rds.aws_db_instance.main

# List all resources in state
terraform state list

# Get resource address for import
terraform state list | grep vpc
```

### Use Terraform Console

```bash
# Interactive console for expressions
terraform console

# Test variable interpolation
> var.environment
"dev"

# Test module outputs
> module.vpc.vpc_id
"vpc-0a1b2c3d4e5f6g7h8"

# Test functions
> cidrsubnet("10.0.0.0/16", 8, 1)
"10.0.1.0/24"

# Exit console
> exit
```

### Visualize Terraform Dependency Graph

```bash
# Generate dependency graph
terraform graph | dot -Tpng > graph.png

# Or use online tool
terraform graph > graph.dot
# Upload graph.dot to https://dreampuf.github.io/GraphvizOnline/
```

### Validate Terraform Configuration

```bash
# Check syntax and configuration
terraform validate

# Format code
terraform fmt -recursive

# Check formatting without changes
terraform fmt -check -recursive

# Run tflint for AWS best practices
tflint --recursive
```

## State Corruption Recovery

### Scenario: State File is Empty or Corrupted

**Steps:**
1. **Backup Current State:**
```bash
cp .terraform/terraform.tfstate terraform.tfstate.corrupted
```

2. **List Available State Versions:**
```bash
aws s3api list-object-versions \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --prefix workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate \
  --query 'Versions[*].[VersionId,LastModified,Size]' \
  --output table
```

3. **Download Previous Working Version:**
```bash
aws s3api get-object \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --key workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate \
  --version-id <previous-working-version-id> \
  terraform.tfstate.recovered
```

4. **Verify Recovered State:**
```bash
# Check if state is valid JSON
jq . terraform.tfstate.recovered

# Check terraform can read it
terraform show -json terraform.tfstate.recovered | jq .
```

5. **Replace Corrupted State:**
```bash
cp terraform.tfstate.recovered .terraform/terraform.tfstate
```

6. **Refresh State:**
```bash
terraform refresh -var-file="terraform.tfvars.$(terraform workspace show)"
```

7. **Verify Resources:**
```bash
terraform plan -var-file="terraform.tfvars.$(terraform workspace show)"
# Should show minimal changes
```

### Scenario: State Out of Sync with Reality

**Steps:**
1. **Identify Drift:**
```bash
terraform plan -var-file="terraform.tfvars.$(terraform workspace show)"
# Review resources to be created/destroyed
```

2. **For Resources Terraform Thinks Don't Exist (but do):**
```bash
# Import resources back into state
terraform import module.vpc.aws_vpc.main vpc-xxxxx
terraform import module.rds.aws_db_instance.main hipaa-db-dev
```

3. **For Resources Terraform Doesn't Know About:**
```bash
# Remove from state (they still exist in AWS)
terraform state rm module.vpc.aws_subnet.public[2]

# Re-import with correct configuration
terraform import module.vpc.aws_subnet.public[2] subnet-xxxxx
```

4. **Refresh State:**
```bash
terraform refresh -var-file="terraform.tfvars.$(terraform workspace show)"
```

## Resource Import Procedures

### Import VPC Resources

```bash
# Import VPC
terraform import module.vpc.aws_vpc.main vpc-xxxxx

# Import subnets (use index matching configuration)
terraform import 'module.vpc.aws_subnet.public[0]' subnet-xxxxx
terraform import 'module.vpc.aws_subnet.public[1]' subnet-yyyyy
terraform import 'module.vpc.aws_subnet.public[2]' subnet-zzzzz

terraform import 'module.vpc.aws_subnet.private[0]' subnet-aaaaa
terraform import 'module.vpc.aws_subnet.private[1]' subnet-bbbbb
terraform import 'module.vpc.aws_subnet.private[2]' subnet-ccccc

# Import internet gateway
terraform import module.vpc.aws_internet_gateway.main igw-xxxxx

# Import NAT gateways
terraform import 'module.vpc.aws_nat_gateway.main[0]' nat-xxxxx
terraform import 'module.vpc.aws_nat_gateway.main[1]' nat-yyyyy
terraform import 'module.vpc.aws_nat_gateway.main[2]' nat-zzzzz

# Import VPC endpoints
terraform import module.vpc.aws_vpc_endpoint.s3 vpce-xxxxx
terraform import module.vpc.aws_vpc_endpoint.rds vpce-yyyyy
```

### Import RDS Instance

```bash
# Import DB instance
terraform import module.rds.aws_db_instance.main hipaa-db-dev

# Import DB subnet group
terraform import module.rds.aws_db_subnet_group.main dev-rds-subnet-group

# Import DB parameter group
terraform import module.rds.aws_db_parameter_group.main dev-postgres15-pgvector

# If read replica exists
terraform import 'module.rds.aws_db_instance.read_replica[0]' hipaa-db-dev-replica
```

### Import S3 Buckets

```bash
# Import buckets
terraform import module.s3.aws_s3_bucket.documents hipaa-compliant-docs-dev-123456789012
terraform import module.s3.aws_s3_bucket.backups hipaa-compliant-backups-dev-123456789012
terraform import module.s3.aws_s3_bucket.audit_logs hipaa-compliant-audit-dev-123456789012

# Import bucket configurations
terraform import module.s3.aws_s3_bucket_versioning.documents hipaa-compliant-docs-dev-123456789012
terraform import module.s3.aws_s3_bucket_server_side_encryption_configuration.documents hipaa-compliant-docs-dev-123456789012
terraform import module.s3.aws_s3_bucket_public_access_block.documents hipaa-compliant-docs-dev-123456789012
```

### Import KMS Key

```bash
# Import KMS key
terraform import module.kms.aws_kms_key.master arn:aws:kms:us-east-1:123456789012:key/xxxxx

# Import KMS alias
terraform import module.kms.aws_kms_alias.master alias/hipaa-master-dev
```

### Import IAM Resources

```bash
# Import IAM role
terraform import module.iam.aws_iam_role.backend_app hipaa-app-backend-dev

# Import IAM policies
terraform import module.iam.aws_iam_policy.s3_access arn:aws:iam::123456789012:policy/dev-s3-access-policy
terraform import module.iam.aws_iam_policy.kms_access arn:aws:iam::123456789012:policy/dev-kms-access-policy

# Import policy attachments
terraform import module.iam.aws_iam_role_policy_attachment.s3 hipaa-app-backend-dev/arn:aws:iam::123456789012:policy/dev-s3-access-policy
```

### Import Security Groups

```bash
# Import security groups
terraform import module.networking.aws_security_group.rds sg-xxxxx
terraform import module.networking.aws_security_group.app sg-yyyyy
terraform import module.networking.aws_security_group.vpc_endpoints sg-zzzzz

# Import security group rules (if managed separately)
terraform import 'module.networking.aws_security_group_rule.rds_ingress[0]' sg-xxxxx_ingress_tcp_5432_5432_sg-yyyyy
```

## Getting Help

### AWS Console Verification

When debugging Terraform issues, verify resources in AWS Console:
- **VPC Dashboard:** Check VPC, subnets, route tables, internet gateway, NAT gateways
- **RDS Dashboard:** Check DB instances, snapshots, parameter groups, subnet groups
- **S3 Console:** Check buckets, versioning, encryption, lifecycle policies
- **KMS Console:** Check keys, key policies, rotation status, aliases
- **IAM Console:** Check roles, policies, policy attachments
- **Config Dashboard:** Check recorder status, rules, compliance status
- **CloudTrail:** Check recent API activity for errors

### Terraform Documentation

- Official Docs: https://www.terraform.io/docs
- AWS Provider: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- Module Registry: https://registry.terraform.io/browse/modules

### Support Channels

- GitHub Issues: Check project repository
- Terraform Community: https://discuss.hashicorp.com/
- AWS Support: https://console.aws.amazon.com/support/
- Internal DevOps Team: Contact for project-specific help

## Prevention and Best Practices

### Before Every Terraform Operation

1. **Backup State:**
```bash
aws s3 cp \
  s3://terraform-state-hipaa-${AWS_ACCOUNT_ID}/workspaces/$(terraform workspace show)/hipaa-infrastructure/terraform.tfstate \
  terraform.tfstate.backup-$(date +%Y%m%d-%H%M%S)
```

2. **Review Plan:**
```bash
terraform plan -var-file="terraform.tfvars.$(terraform workspace show)" -out=tfplan
# Carefully review output before applying
```

3. **Verify Workspace:**
```bash
terraform workspace show
# Confirm you're in correct environment (dev/staging/production)
```

4. **Check for Drift:**
```bash
terraform refresh -var-file="terraform.tfvars.$(terraform workspace show)"
terraform plan -var-file="terraform.tfvars.$(terraform workspace show)"
```

### Regular Maintenance

1. **Weekly:** Run `terraform plan` to detect drift
2. **Monthly:** Review AWS Config compliance reports
3. **Quarterly:** Update Terraform and provider versions
4. **Annually:** Review and optimize infrastructure costs
