# HIPAA-Compliant AWS Infrastructure (Terraform)

This directory contains Infrastructure as Code (IaC) for provisioning all AWS resources required for the HIPAA-compliant multi-tenant document management system.

## Overview

The Terraform configuration provisions:
- **VPC**: Multi-AZ network architecture with public/private subnets
- **RDS**: PostgreSQL database with pgvector extension, encryption, and automated backups
- **S3**: Document storage, backups, and audit log buckets with lifecycle policies
- **KMS**: Master encryption key with automatic rotation
- **IAM**: Least-privilege roles and policies for backend application
- **Security Groups**: Network access controls with default-deny rules
- **AWS Config**: Continuous compliance monitoring with automated rule checks
- **VPC Endpoints**: Private connectivity to AWS services without NAT gateway costs

## Directory Structure

```
terraform/
├── main.tf                      # Root configuration orchestrating all modules
├── variables.tf                 # Input variables for all modules
├── outputs.tf                   # Outputs for Railway integration
├── versions.tf                  # Terraform and provider version constraints
├── backend.tf                   # S3 backend configuration for state management
├── terraform.tfvars.dev         # Development environment variables
├── terraform.tfvars.staging     # Staging environment variables
├── terraform.tfvars.production  # Production environment variables
├── modules/
│   ├── vpc/                     # VPC, subnets, routing, NAT gateways, VPC endpoints
│   ├── networking/              # Security groups and network ACLs
│   ├── kms/                     # KMS master key for infrastructure encryption
│   ├── s3/                      # S3 buckets with encryption and lifecycle policies
│   ├── rds/                     # PostgreSQL with pgvector, Multi-AZ, read replicas
│   ├── iam/                     # IAM roles and policies for backend application
│   └── config/                  # AWS Config rules for compliance monitoring
└── README.md                    # This file
```

## Prerequisites

### Required Tools
- **Terraform CLI**: >= 1.5.0 ([Download](https://www.terraform.io/downloads))
- **AWS CLI**: >= 2.x ([Download](https://aws.amazon.com/cli/))
- **jq**: For JSON parsing ([Download](https://stedolan.github.io/jq/download/))

### AWS Requirements
- AWS account with administrative access
- AWS credentials configured (access key ID and secret access key)
- Sufficient service quotas for RDS, VPC, and S3 resources

### Initial Setup (One-Time)

#### 1. Configure AWS Credentials

```bash
export AWS_ACCESS_KEY_ID="AKIAXXXXXXXXXXXXXXXX"
export AWS_SECRET_ACCESS_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export AWS_REGION="us-east-1"
```

Or configure via AWS CLI:
```bash
aws configure
```

#### 2. Bootstrap Terraform State Backend

The state backend requires an S3 bucket and DynamoDB table. Create these manually:

```bash
# Replace {account-id} with your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create S3 bucket for state storage
aws s3api create-bucket \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --region us-east-1

# Enable versioning on state bucket
aws s3api put-bucket-versioning \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

#### 3. Update Backend Configuration

Edit `backend.tf` and replace `${aws_account_id}` with your actual AWS account ID, or use backend config flags:

```bash
terraform init \
  -backend-config="bucket=terraform-state-hipaa-${AWS_ACCOUNT_ID}" \
  -backend-config="region=us-east-1" \
  -backend-config="dynamodb_table=terraform-state-lock"
```

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

### 2. Create Workspaces

Workspaces provide environment isolation (dev, staging, production):

```bash
terraform workspace new dev
terraform workspace new staging
terraform workspace new production
```

### 3. Select Target Environment

```bash
terraform workspace select dev
```

### 4. Plan Infrastructure Changes

```bash
terraform plan -var-file="terraform.tfvars.dev" -out=tfplan
```

### 5. Review Plan Output

Carefully review the resources to be created. Verify:
- Encryption is enabled for RDS and S3
- Security groups follow least-privilege rules
- No public endpoints for RDS
- Multi-AZ configuration matches environment expectations

### 6. Apply Infrastructure

```bash
terraform apply tfplan
```

Expected provisioning time: **8-12 minutes** for full stack deployment.

### 7. Export Outputs for Railway

After successful deployment, export outputs to JSON:

```bash
terraform output -json > outputs.json
```

This file is consumed by the backend application via `scripts/load-terraform-outputs.sh`.

## Environment-Specific Deployment

### Development Environment

**Configuration**: `terraform.tfvars.dev`

**Characteristics**:
- Cost-optimized (db.t3.medium, single-AZ)
- 7-day backup retention
- No read replicas
- Deletion protection disabled

**Monthly Cost**: ~$100-150

```bash
terraform workspace select dev
terraform plan -var-file="terraform.tfvars.dev"
terraform apply -var-file="terraform.tfvars.dev"
```

### Staging Environment

**Configuration**: `terraform.tfvars.staging`

**Characteristics**:
- Production-like (db.t3.large, Multi-AZ)
- 30-day backup retention
- No read replicas
- Deletion protection disabled

**Monthly Cost**: ~$250-350

```bash
terraform workspace select staging
terraform plan -var-file="terraform.tfvars.staging"
terraform apply -var-file="terraform.tfvars.staging"
```

### Production Environment

**Configuration**: `terraform.tfvars.production`

**Characteristics**:
- High availability (db.r6g.xlarge, Multi-AZ)
- Read replicas enabled
- 30-day backup retention
- Deletion protection enabled

**Monthly Cost**: ~$500-800 (without reserved instances)

```bash
terraform workspace select production
terraform plan -var-file="terraform.tfvars.production"
terraform apply -var-file="terraform.tfvars.production"
```

## Workspace Management

### List Workspaces
```bash
terraform workspace list
```

### Show Current Workspace
```bash
terraform workspace show
```

### Switch Workspace
```bash
terraform workspace select staging
```

### Delete Workspace (after destroying resources)
```bash
terraform workspace select default
terraform workspace delete dev
```

## Common Operations

### View Current State
```bash
terraform show
```

### Inspect Specific Resource
```bash
terraform state show module.rds.aws_db_instance.main
```

### Refresh State
```bash
terraform refresh -var-file="terraform.tfvars.dev"
```

### Format Terraform Files
```bash
terraform fmt -recursive
```

### Validate Configuration
```bash
terraform validate
```

### Destroy Infrastructure
```bash
terraform destroy -var-file="terraform.tfvars.dev"
```

**WARNING**: Destroying production infrastructure will permanently delete data. Always create manual snapshots first.

## Output Variables

The following outputs are exported for Railway integration:

| Output | Description |
|--------|-------------|
| `rds_endpoint` | PostgreSQL connection endpoint (host:port) |
| `rds_reader_endpoint` | Read replica endpoint (if enabled) |
| `s3_bucket_documents` | Documents bucket name |
| `s3_bucket_backups` | Backups bucket name |
| `s3_bucket_audit_logs` | Audit logs bucket name |
| `kms_master_key_id` | KMS master key ID |
| `kms_master_key_arn` | KMS master key ARN |
| `vpc_id` | VPC ID |
| `app_iam_role_arn` | Backend application IAM role ARN |
| `aws_region` | AWS region |
| `environment` | Environment name |

## Module Documentation

Each module has its own README with detailed documentation:

- [VPC Module](./modules/vpc/README.md)
- [Networking Module](./modules/networking/README.md)
- [KMS Module](./modules/kms/README.md)
- [S3 Module](./modules/s3/README.md)
- [RDS Module](./modules/rds/README.md)
- [IAM Module](./modules/iam/README.md)
- [Config Module](./modules/config/README.md)

## State Management

### Remote State Backend
- **Storage**: S3 bucket with versioning enabled
- **Locking**: DynamoDB table prevents concurrent modifications
- **Encryption**: State file encrypted at rest using S3 SSE
- **Workspace Isolation**: Each workspace has separate state file

### State Recovery

If state becomes corrupted, restore from S3 version history:

```bash
# List state file versions
aws s3api list-object-versions \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --prefix workspaces/dev/hipaa-infrastructure/terraform.tfstate

# Download specific version
aws s3api get-object \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --key workspaces/dev/hipaa-infrastructure/terraform.tfstate \
  --version-id {version-id} \
  terraform.tfstate.backup
```

## Troubleshooting

### Common Issues

**Issue**: `Error: Backend initialization required`
**Solution**: Run `terraform init` to initialize backend and download providers.

**Issue**: `Error: Workspace already exists`
**Solution**: Select existing workspace with `terraform workspace select dev`.

**Issue**: `Error: Insufficient permissions`
**Solution**: Verify AWS credentials have administrative access.

**Issue**: `Error: Resource already exists`
**Solution**: Import existing resource: `terraform import module.vpc.aws_vpc.main vpc-xxxxx`

**Issue**: RDS provisioning timeout
**Solution**: RDS takes 10-15 minutes. Increase timeout or wait and retry.

### Debugging

Enable Terraform debug logging:
```bash
export TF_LOG=DEBUG
export TF_LOG_PATH=./terraform-debug.log
terraform apply
```

## Security Considerations

### Encryption
- **RDS**: Encrypted at rest using KMS, TLS 1.2+ for connections
- **S3**: SSE-KMS encryption for all buckets
- **State File**: Encrypted in S3 backend

### Access Controls
- **IAM Policies**: Least-privilege access with specific resource ARNs
- **Security Groups**: Default-deny with explicit allow rules
- **No Public Endpoints**: RDS in private subnets, S3 via VPC endpoints

### Audit Logging
- **CloudTrail**: All API calls logged to audit bucket
- **AWS Config**: Resource configuration changes tracked
- **S3 Access Logs**: Bucket access logged to audit bucket

## HIPAA Compliance

This infrastructure addresses HIPAA technical safeguards:

| Requirement | Implementation |
|-------------|----------------|
| **Encryption at Rest** | KMS encryption for RDS and S3 |
| **Encryption in Transit** | TLS 1.2+ enforced for all connections |
| **Access Controls** | IAM policies, security groups, RLS (application-level) |
| **Audit Logging** | CloudTrail, AWS Config, application audit logs |
| **Backup & Recovery** | Automated RDS snapshots (30-day retention), S3 versioning |
| **Data Retention** | 7-year S3 lifecycle policy (HIPAA requirement) |

## Cost Optimization

### S3 Lifecycle Policies
- Standard → Standard-IA: 90 days (46% savings)
- Standard-IA → Glacier: 365 days (83% savings)
- Expiration: 2555 days (7 years, HIPAA requirement)

### VPC Endpoints
- Use gateway endpoint for S3 (free)
- Avoid NAT gateway data transfer charges ($0.045/GB)
- Estimated savings: $93/month (for 1TB data transfer)

### RDS Reserved Instances
- Production: Consider 1-year or 3-year reserved instances (up to 72% savings)
- Staging: On-demand or convertible reserved instances

## Testing

This project includes comprehensive automated testing using [Terratest](https://terratest.gruntwork.io/).

### Test Structure

```
tests/
├── unit/                    # Module-specific tests (49 tests)
│   ├── kms_test.go         # KMS module tests (8 tests)
│   ├── vpc_test.go         # VPC module tests (8 tests)
│   ├── s3_test.go          # S3 module tests (6 tests)
│   ├── iam_test.go         # IAM module tests (7 tests)
│   ├── rds_test.go         # RDS module tests (8 tests)
│   ├── networking_test.go  # Networking tests (3 tests)
│   ├── config_test.go      # AWS Config tests (8 tests)
│   └── sample_test.go      # Sample test setup
└── integration/            # End-to-end tests (7 tests)
    ├── full_stack_test.go           # Complete stack deployment
    └── security_compliance_test.go  # HIPAA compliance validation
```

### Test Features

- **Parallel Execution**: Tests run in parallel using `t.Parallel()`
- **Automatic Cleanup**: All resources cleaned up with `defer terraform.Destroy()`
- **Dynamic Account IDs**: Tests use `aws.GetAccountId(t)` for portability across AWS accounts
- **Unique Resource Names**: Generated using `random.UniqueId()` with lowercase conversion
- **Environment Validation**: Tests validate the `name_suffix` architecture

### Running Tests

#### Prerequisites
```bash
# Install Go dependencies
cd tests
go mod download

# Configure AWS credentials
export AWS_PROFILE=terraform-test
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

#### Run All Unit Tests
```bash
cd tests
source ~/.zshrc  # Load AWS credentials
go test -v -timeout 60m ./unit/...
```

#### Run Specific Module Tests
```bash
# KMS module tests (validated ✅)
go test -v -timeout 15m -run TestKMS ./unit/

# VPC module tests
go test -v -timeout 15m -run TestVPC ./unit/

# S3 module tests
go test -v -timeout 15m -run TestS3 ./unit/

# IAM module tests
go test -v -timeout 15m -run TestIAM ./unit/

# RDS module tests
go test -v -timeout 30m -run TestRDS ./unit/

# Networking module tests
go test -v -timeout 15m -run TestNetworking ./unit/

# Config module tests
go test -v -timeout 15m -run TestConfig ./unit/
```

#### Run Integration Tests
```bash
# WARNING: Creates complete infrastructure stack (~25-30 minutes)
cd tests
go test -v -timeout 90m -run TestFullStackDeployment ./integration/

# HIPAA compliance tests
go test -v -timeout 30m -run TestHIPAA ./integration/
```

#### Run Single Test
```bash
# Example: Run only KMS key creation test
go test -v -timeout 10m -run TestKMSKeyCreation$ ./unit/
```

### Test Results

✅ **Code compilation**: All tests compile successfully
✅ **Dynamic account ID**: KMS test passed (35s) validating dynamic AWS account lookup
✅ **Test coverage**: 49 unit tests + 7 integration tests = 56 total tests

### Available Tests

**Unit Tests (49 total)**:
- KMS: TestKMSKeyCreation, TestKMSKeyRotationEnabled, TestKMSKeyRotationDisabled, TestKMSKeyAlias, TestKMSKeyPolicy, TestKMSMultipleEnvironments, TestKMSKeyTags, TestKMSInvalidEnvironment
- VPC: TestVPCCreation, TestSubnetCreation, TestInternetGateway, TestNATGatewayCreation, TestNATGatewayDisabled, TestRouteTables, TestVPCEndpointsEnabled, TestVPCEndpointsDisabled
- S3: TestS3ModuleBucketCreation, TestS3ModuleEncryption, TestS3ModuleVersioning, TestS3ModulePublicAccessBlock, TestS3ModuleOutputs, TestS3ModuleMinimalInputs
- IAM: TestIAMModuleRoleCreation, TestIAMModulePoliciesCreated, TestIAMModuleRDSMonitoringRoleConditional, TestIAMModuleRDSMonitoringRoleDisabled, TestIAMModuleEnvironmentTagging, TestIAMModuleAllOutputs, TestIAMModuleWithMinimalInputs
- RDS: TestRDSSubnetGroupCreation, TestRDSInstanceCreation, TestRDSParameterGroupWithPgVector, TestRDSInstanceEncryptionEnabled, TestRDSBackupConfiguration, TestRDSMultiAZConfiguration, TestRDSReadReplicaConditional, TestRDSOutputsPopulated
- Networking: TestAppSecurityGroupConfiguration, TestSecurityGroupsEnvironmentTagging, TestSecurityGroupsWithEmptyRailwayIPRanges, TestVPCEndpointSecurityGroup, TestRDSSecurityGroupIngressRules
- Config: TestConfigModuleRecorderCreation, TestConfigModuleDeliveryChannel, TestConfigModuleRulesDeployment, TestConfigModuleSNSTopicCreation, TestConfigModuleWithEmailSubscription, TestConfigModuleEnvironmentValidation, TestConfigModuleTagsPropagation, TestConfigModuleBasicDeployment

**Integration Tests (7 total)**:
- TestFullStackDeployment: Complete infrastructure deployment
- TestHIPAAEncryptionCompliance: Validates encryption at rest and in transit
- TestNetworkIsolation: Validates private subnet isolation
- TestVPCEndpointConnectivity: Validates VPC endpoint connectivity
- TestIAMLeastPrivilege: Validates IAM policies follow least privilege
- TestAuditLogging: Validates audit logging configuration
- TestBackupAndRecovery: Validates backup and recovery processes

### Test Costs

**WARNING**: Tests create real AWS resources and will incur costs.

- **Unit Tests**: ~$0.50-2.00 per test run (resources destroyed after each test)
- **Integration Tests**: ~$5.00-10.00 per run (full stack deployment)
- **Recommendation**: Run tests selectively in development; use CI/CD for full suite

### Test Architecture

Tests use the `name_suffix` pattern for resource isolation:

```go
environment := "dev"
nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))
awsAccountID := aws.GetAccountId(t)

terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
    Vars: map[string]interface{}{
        "environment":    environment,    // dev (validated)
        "name_suffix":    nameSuffix,     // test-abc123 (unique)
        "aws_account_id": awsAccountID,   // 873125487926 (dynamic)
    },
})
```

This produces resource names like: `hipaa-compliant-docs-dev-test-abc123-873125487926`

## Name Suffix Architecture

The `name_suffix` variable provides flexible resource naming for different use cases:

### Production Deployment
```hcl
environment = "dev"
name_suffix = ""  # Empty for clean production names
```
**Result**: `hipaa-compliant-docs-dev-873125487926`

### Test Runs
```hcl
environment = "dev"
name_suffix = "test-abc123"  # Unique test identifier
```
**Result**: `hipaa-compliant-docs-dev-test-abc123-873125487926`

### Developer Environments
```hcl
environment = "dev"
name_suffix = "jsmith"  # Personal identifier
```
**Result**: `hipaa-compliant-docs-dev-jsmith-873125487926`

### Validation Rules

The `name_suffix` variable has strict validation:

```hcl
validation {
  condition     = can(regex("^[a-z0-9-]*$", var.name_suffix))
  error_message = "name_suffix may contain only lowercase letters, digits, and hyphens."
}
```

Benefits:
- **Parallel Testing**: Multiple test runs can execute simultaneously without resource conflicts
- **Developer Isolation**: Each developer can have their own infrastructure
- **Clean Production**: Production resources have simple, predictable names
- **Audit Trail**: Resource names clearly indicate their purpose and owner

## Support

For issues or questions:
1. Check module-specific README files
2. Review Terraform documentation: https://www.terraform.io/docs
3. Review AWS documentation: https://docs.aws.amazon.com
4. Consult deployment guide: `docs/TERRAFORM_DEPLOYMENT.md` (if available)
5. Review test documentation: `tests/README.md` (if available)

## License

See `LICENSE` file in repository root.

---

**Last Updated**: 2025-10-18
**Terraform Version**: >= 1.5.0
**AWS Provider Version**: >= 5.0
**Test Coverage**: 49 unit tests + 7 integration tests = 56 total tests
**Test Status**: ✅ Compilation verified, KMS test passed
