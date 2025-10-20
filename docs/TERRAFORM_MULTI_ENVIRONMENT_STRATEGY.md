# Terraform Multi-Environment Strategy

Strategy and best practices for managing multiple environments (dev, staging, production) with Terraform.

## Table of Contents

1. [Overview](#overview)
2. [Workspace Strategy](#workspace-strategy)
3. [Environment Variable Management](#environment-variable-management)
4. [Promotion Workflow](#promotion-workflow)
5. [AWS Account Separation](#aws-account-separation)
6. [Testing Strategy](#testing-strategy)

## Overview

### Environment Goals

| Environment | Purpose | Audience | Uptime Requirement |
|-------------|---------|----------|-------------------|
| **Development** | Feature development, experimentation | Developers | Best effort (can be stopped) |
| **Staging** | Pre-production testing, QA | QA team, Product | High (production-like) |
| **Production** | Live customer data | End users | Critical (99.9%+) |

### Infrastructure Differences

| Component | Development | Staging | Production |
|-----------|-------------|---------|------------|
| **RDS Instance** | db.t3.medium, Single-AZ | db.t3.large, Multi-AZ | db.r6g.xlarge, Multi-AZ + Replica |
| **RDS Storage** | 20GB | 50GB | 100GB |
| **RDS Backups** | 7 days | 30 days | 30 days |
| **Deletion Protection** | Disabled | Disabled | Enabled |
| **NAT Gateways** | 1 (single-AZ) | 3 (multi-AZ) | 3 (multi-AZ) |
| **Cost** | ~$73/month | ~$315/month | ~$520/month (with RI) |

---

## Workspace Strategy

### Terraform Workspaces

**Configuration:**
```bash
# Initialize workspaces
terraform workspace new dev
terraform workspace new staging
terraform workspace new production

# List workspaces
terraform workspace list

# Select workspace
terraform workspace select dev
```

**Workspace Isolation:**
- Each workspace has separate state file in S3
- State path: `s3://terraform-state-bucket/workspaces/{workspace}/terraform.tfstate`
- Resources tagged with `Environment = {workspace}`
- No resource name conflicts between environments

**Advantages:**
- Simple workflow (single codebase)
- Consistent configuration across environments
- Easy to promote changes from dev → staging → production

**Disadvantages:**
- All environments share same AWS account (unless using account separation)
- Accidental resource deletion risk if wrong workspace selected
- Limited environment-specific customization

---

### Environment-Specific Variable Files

**terraform.tfvars.dev:**
```hcl
environment              = "dev"
aws_region               = "us-east-1"
vpc_cidr                 = "10.0.0.0/16"

# RDS Configuration
rds_instance_class       = "db.t3.medium"
rds_allocated_storage    = 20
rds_multi_az             = false
enable_read_replica      = false
rds_backup_retention     = 7
deletion_protection      = false

# Networking
enable_nat_gateway       = true
nat_gateway_count        = 1  # Cost optimization
enable_vpc_endpoints     = true

# Config
sns_alert_email          = "devops-dev@organization.com"
enable_auto_remediation  = false
```

**terraform.tfvars.production:**
```hcl
environment              = "production"
aws_region               = "us-east-1"
vpc_cidr                 = "10.1.0.0/16"  # Different CIDR to avoid conflicts

# RDS Configuration
rds_instance_class       = "db.r6g.xlarge"
rds_allocated_storage    = 100
rds_multi_az             = true
enable_read_replica      = true
rds_backup_retention     = 30
deletion_protection      = true

# Networking
enable_nat_gateway       = true
nat_gateway_count        = 3  # High availability
enable_vpc_endpoints     = true

# Config
sns_alert_email          = "devops-prod@organization.com"
enable_auto_remediation  = false
```

---

## Environment Variable Management

### Railway Environment Variables (Per Environment)

**Development:**
```bash
# User-provided
AWS_ACCESS_KEY_ID=AKIADEV...
AWS_SECRET_ACCESS_KEY=...
ENVIRONMENT=dev
OIDC_CLIENT_ID=dev-client-id

# Auto-generated from Terraform outputs
DATABASE_URL=postgresql://...:5432/hipaa_db
S3_BUCKET_DOCUMENTS=hipaa-compliant-docs-dev-123456789012
KMS_MASTER_KEY_ID=arn:aws:kms:...
```

**Production:**
```bash
# User-provided
AWS_ACCESS_KEY_ID=AKIAPROD...
AWS_SECRET_ACCESS_KEY=...
ENVIRONMENT=production
OIDC_CLIENT_ID=prod-client-id

# Auto-generated from Terraform outputs
DATABASE_URL=postgresql://...:5432/hipaa_db
S3_BUCKET_DOCUMENTS=hipaa-compliant-docs-production-123456789012
KMS_MASTER_KEY_ID=arn:aws:kms:...
```

**Variable Naming Convention:**
- Environment-specific: `AWS_ACCESS_KEY_ID_DEV`, `AWS_ACCESS_KEY_ID_PROD`
- Shared naming: `DATABASE_URL`, `S3_BUCKET_DOCUMENTS` (Railway handles env-specific injection)

---

## Promotion Workflow

### Infrastructure Code Promotion

**Workflow: Dev → Staging → Production**

```bash
# 1. Develop and test in dev environment
terraform workspace select dev
terraform plan -var-file="terraform.tfvars.dev" -out=tfplan.dev
terraform apply tfplan.dev

# 2. Test application with new infrastructure
curl https://dev.railway.app/api/v1/health/ready

# 3. Merge to staging branch (triggers staging deployment)
git checkout staging
git merge dev
git push origin staging

# 4. Deploy to staging
terraform workspace select staging
terraform plan -var-file="terraform.tfvars.staging" -out=tfplan.staging
terraform apply tfplan.staging

# 5. Run QA tests on staging
./scripts/run-qa-tests.sh staging

# 6. Create pull request for production deployment
git checkout main
git merge staging
gh pr create --title "Production deployment - $(date +%Y-%m-%d)" \
  --body "Changes tested in dev and staging"

# 7. After PR approval, deploy to production
terraform workspace select production
terraform plan -var-file="terraform.tfvars.production" -out=tfplan.production

# Review plan carefully
# Create manual RDS snapshot
aws rds create-db-snapshot \
  --db-instance-identifier hipaa-db-production \
  --db-snapshot-identifier pre-deploy-$(date +%Y%m%d-%H%M%S)

terraform apply tfplan.production

# 8. Verify production deployment
curl https://production.railway.app/api/v1/health/ready
./scripts/smoke-tests.sh production
```

---

### Rollback Workflow

**Rollback Production Deployment:**
```bash
# 1. Revert Git commit
git revert <commit-hash>
git push origin main

# 2. Restore previous Terraform state (if needed)
aws s3api list-object-versions \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --prefix workspaces/production/hipaa-infrastructure/terraform.tfstate

aws s3api get-object \
  --bucket terraform-state-hipaa-${AWS_ACCOUNT_ID} \
  --key workspaces/production/hipaa-infrastructure/terraform.tfstate \
  --version-id <previous-version-id> \
  terraform.tfstate.rollback

cp terraform.tfstate.rollback .terraform/terraform.tfstate

# 3. Apply previous configuration
terraform apply -var-file="terraform.tfvars.production"

# 4. Verify rollback successful
curl https://production.railway.app/api/v1/health/ready
```

---

## AWS Account Separation

### Recommended AWS Organization Structure

```
Root Account (Management)
├── dev-account (123456789012)
│   ├── VPC: 10.0.0.0/16
│   ├── RDS: hipaa-db-dev
│   └── S3: hipaa-compliant-docs-dev-*
├── staging-account (234567890123)
│   ├── VPC: 10.1.0.0/16
│   ├── RDS: hipaa-db-staging
│   └── S3: hipaa-compliant-docs-staging-*
└── production-account (345678901234)
    ├── VPC: 10.2.0.0/16
    ├── RDS: hipaa-db-production
    └── S3: hipaa-compliant-docs-production-*
```

**Benefits:**
- **Cost Isolation:** Separate billing per environment
- **Security Isolation:** No cross-account access without explicit trust
- **Compliance Isolation:** Production audits don't affect dev
- **Resource Limit Isolation:** Dev experiments don't exhaust production quotas

**Implementation:**
```bash
# 1. Create AWS Organization
aws organizations create-organization

# 2. Create member accounts
aws organizations create-account \
  --email dev-aws@organization.com \
  --account-name "HIPAA Dev Account"

aws organizations create-account \
  --email staging-aws@organization.com \
  --account-name "HIPAA Staging Account"

aws organizations create-account \
  --email production-aws@organization.com \
  --account-name "HIPAA Production Account"

# 3. Configure cross-account access (assume role)
# Create IAM role in each account allowing root account access
```

**Terraform Configuration with Multiple Accounts:**
```hcl
# terraform/providers.tf
provider "aws" {
  alias  = "dev"
  region = "us-east-1"
  assume_role {
    role_arn = "arn:aws:iam::123456789012:role/TerraformDeployRole"
  }
}

provider "aws" {
  alias  = "production"
  region = "us-east-1"
  assume_role {
    role_arn = "arn:aws:iam::345678901234:role/TerraformDeployRole"
  }
}

# Use provider in modules
module "vpc" {
  source = "./modules/vpc"
  providers = {
    aws = aws.production
  }
}
```

---

## Testing Strategy

### Per-Environment Testing

**Development Environment:**
- **Purpose:** Developer integration testing
- **Test Scope:** Unit tests, integration tests, manual testing
- **Test Data:** Synthetic test data only
- **Test Frequency:** Continuous (on every commit)

**Staging Environment:**
- **Purpose:** QA and pre-production validation
- **Test Scope:** Full regression suite, load testing, security testing
- **Test Data:** Sanitized production-like data
- **Test Frequency:** On every PR to main branch

**Production Environment:**
- **Purpose:** Live customer workloads
- **Test Scope:** Smoke tests, health checks, synthetic monitoring
- **Test Data:** Real customer PHI (HIPAA-protected)
- **Test Frequency:** On every deployment + continuous monitoring

---

### Infrastructure Testing Pipeline

```yaml
# .github/workflows/terraform-multi-env.yml
name: Terraform Multi-Environment Pipeline

on:
  pull_request:
    branches: [main]
  push:
    branches: [dev, staging, main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: hashicorp/setup-terraform@v2

      # Validate all environment configurations
      - name: Terraform Validate (Dev)
        run: terraform validate
        working-directory: terraform

      - name: Terraform Plan (Dev)
        run: terraform plan -var-file="terraform.tfvars.dev"
        working-directory: terraform

      - name: Terraform Plan (Staging)
        run: terraform plan -var-file="terraform.tfvars.staging"
        working-directory: terraform

      - name: Terraform Plan (Production)
        run: terraform plan -var-file="terraform.tfvars.production"
        working-directory: terraform

  deploy-dev:
    needs: test
    if: github.ref == 'refs/heads/dev'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Dev
        run: |
          terraform workspace select dev
          terraform apply -var-file="terraform.tfvars.dev" -auto-approve

  deploy-staging:
    needs: test
    if: github.ref == 'refs/heads/staging'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Staging
        run: |
          terraform workspace select staging
          terraform apply -var-file="terraform.tfvars.staging" -auto-approve

  deploy-production:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production  # Requires manual approval
    steps:
      - name: Deploy to Production
        run: |
          terraform workspace select production
          terraform apply -var-file="terraform.tfvars.production" -auto-approve
```

---

## Best Practices

### Environment Naming

**Consistent Naming:**
- AWS Resources: `hipaa-{resource}-{environment}-{account-id}`
- Terraform Workspaces: `dev`, `staging`, `production` (lowercase)
- Git Branches: `dev`, `staging`, `main` (production)
- Railway Projects: `hipaa-dev`, `hipaa-staging`, `hipaa-production`

**Tagging Strategy:**
```hcl
locals {
  common_tags = {
    Environment  = var.environment
    Project      = "HIPAA-Compliant-Document-Management"
    ManagedBy    = "Terraform"
    CostCenter   = "Engineering"
    Compliance   = "HIPAA"
    Owner        = "devops-team@organization.com"
  }
}
```

---

### Environment-Specific Safeguards

**Production Safeguards:**
```hcl
# terraform.tfvars.production
deletion_protection      = true   # Cannot delete RDS without explicit disable
force_destroy            = false  # Cannot delete S3 buckets with Terraform
multi_az                 = true   # High availability required
enable_read_replica      = true   # Disaster recovery

# Require manual approval for production changes
```

**Development Safeguards:**
```hcl
# terraform.tfvars.dev
deletion_protection      = false  # Allow easy cleanup
force_destroy            = true   # Allow Terraform destroy
multi_az                 = false  # Cost optimization
enable_read_replica      = false  # Not needed for dev
```

---

### Change Management Process

**Development Changes:** Direct apply (no approval)
**Staging Changes:** Code review required
**Production Changes:** Code review + manual approval + change request

**Production Change Request Template:**
```markdown
## Production Infrastructure Change Request

**Date:** [Date]
**Requestor:** [Name]
**Terraform Workspace:** production

### Change Description
[Describe what infrastructure changes will be made]

### Terraform Plan Output
```
[Paste terraform plan output here]
```

### Downtime Impact
- [ ] No downtime
- [ ] Minimal downtime (< 5 minutes)
- [ ] Significant downtime (schedule maintenance window)

### Rollback Plan
[Describe how to rollback if changes fail]

### Verification Steps
1. [Step 1 to verify changes]
2. [Step 2 to verify changes]

### Approvals
- [ ] DevOps Lead
- [ ] Engineering Manager
- [ ] CTO (for major changes)
```

---

## Summary

**Key Principles:**
1. **Isolation:** Each environment is isolated (workspaces or accounts)
2. **Consistency:** Same Terraform code, different variables
3. **Promotion:** Dev → Staging → Production workflow
4. **Protection:** Production has additional safeguards
5. **Testing:** Each environment has appropriate test coverage

**Monthly Checklist:**
- [ ] Verify all environments are in sync with Terraform code
- [ ] Review cost differences between environments
- [ ] Test promotion workflow (dev → staging)
- [ ] Verify production safeguards are active

**Quarterly Checklist:**
- [ ] Review AWS account separation strategy
- [ ] Audit environment-specific variable files
- [ ] Test disaster recovery across all environments
- [ ] Update documentation with environment changes
