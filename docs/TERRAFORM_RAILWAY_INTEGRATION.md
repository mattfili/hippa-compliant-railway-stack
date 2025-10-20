# Terraform Railway Integration Guide

Complete guide for integrating Terraform-provisioned AWS infrastructure with Railway-hosted backend application.

## Table of Contents

1. [Overview](#overview)
2. [Railway Project Setup](#railway-project-setup)
3. [Environment Variables Configuration](#environment-variables-configuration)
4. [Terraform Output Wiring](#terraform-output-wiring)
5. [Deployment Workflow](#deployment-workflow)
6. [Troubleshooting](#troubleshooting)

## Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Railway Platform                                            │
│  ┌───────────────────┐      ┌───────────────────────────┐  │
│  │ Terraform Service │──────│ Backend API Service       │  │
│  │ (Deploy Infra)    │      │ (FastAPI + Uvicorn)       │  │
│  └───────────────────┘      └───────────────────────────┘  │
│          │                              │                    │
│          │ outputs.json                 │ Uses env vars      │
│          └──────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
                       │
                       │ Provisions & Connects
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS Infrastructure                                          │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │    VPC     │  │   RDS    │  │    S3    │  │   KMS    │ │
│  │ (Private)  │  │(PostgreSQL)│ │(Buckets) │  │ (Keys)   │ │
│  └────────────┘  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Infrastructure Provisioning:** Railway runs Terraform service to provision AWS resources
2. **Output Export:** Terraform exports infrastructure details to `outputs.json`
3. **Environment Loading:** Backend startup script reads `outputs.json` and exports env vars
4. **Application Connection:** Backend connects to AWS resources using loaded environment variables

---

## Railway Project Setup

### Step 1: Create Railway Project

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link to existing project or create new
railway link
# OR
railway init
```

### Step 2: Configure Railway Services

**Project Structure:**
- Service 1: `terraform` - Provisions AWS infrastructure
- Service 2: `backend` - FastAPI application

**Service Dependencies:**
```json
// railway.json
{
  "$schema": "https://railway.app/railway.schema.json",
  "services": [
    {
      "name": "terraform",
      "build": {
        "builder": "DOCKERFILE",
        "dockerfilePath": "terraform/Dockerfile"
      },
      "deploy": {
        "startCommand": "terraform init && terraform workspace select $ENVIRONMENT && terraform apply -auto-approve && terraform output -json > /app/outputs.json"
      }
    },
    {
      "name": "backend",
      "build": {
        "builder": "DOCKERFILE",
        "dockerfilePath": "backend/Dockerfile"
      },
      "deploy": {
        "startCommand": "sh scripts/startup.sh",
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 3,
        "healthcheckPath": "/api/v1/health/ready",
        "healthcheckTimeout": 30
      },
      "dependsOn": ["terraform"]
    }
  ]
}
```

### Step 3: Configure Terraform Dockerfile for Railway

**terraform/Dockerfile:**
```dockerfile
FROM hashicorp/terraform:1.5

# Install jq for JSON parsing
RUN apk add --no-cache jq

# Copy Terraform configuration
WORKDIR /terraform
COPY . .

# Initialize Terraform
RUN terraform init

# The start command is defined in railway.json
# Railway will run: terraform init && terraform workspace select $ENVIRONMENT && terraform apply -auto-approve && terraform output -json > /app/outputs.json
```

---

## Environment Variables Configuration

### Required Railway Environment Variables

**User-Provided (Set in Railway Dashboard):**

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Environment
ENVIRONMENT=production  # or dev, staging

# RDS Credentials (not in Terraform, set manually)
RDS_PASSWORD=<secure-password-from-secrets-manager>

# OIDC Authentication
OIDC_ISSUER_URL=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxx
OIDC_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxx
OIDC_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Application Configuration
SECRET_KEY=<random-32-char-string>
CORS_ORIGINS=https://frontend.railway.app
```

**Auto-Generated (Loaded from Terraform outputs via startup script):**

These are set dynamically by `backend/scripts/load-terraform-outputs.sh`:

```bash
DATABASE_URL=postgresql+asyncpg://admin_user:${RDS_PASSWORD}@${RDS_ENDPOINT}/hipaa_db
S3_BUCKET_DOCUMENTS=hipaa-compliant-docs-production-123456789012
S3_BUCKET_BACKUPS=hipaa-compliant-backups-production-123456789012
S3_BUCKET_AUDIT_LOGS=hipaa-compliant-audit-production-123456789012
KMS_MASTER_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/xxxxx
KMS_MASTER_KEY_ARN=arn:aws:kms:us-east-1:123456789012:key/xxxxx
VPC_ID=vpc-xxxxx
APP_IAM_ROLE_ARN=arn:aws:iam::123456789012:role/hipaa-app-backend-production
```

### Setting Environment Variables in Railway

**Via Railway Dashboard:**
1. Navigate to Project > Settings > Variables
2. Click "Add Variable"
3. Enter key-value pairs from list above
4. Click "Save"

**Via Railway CLI:**
```bash
# Set single variable
railway variables set AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX

# Set multiple variables from .env file
railway variables set $(cat .env.production)

# List variables
railway variables

# Delete variable
railway variables delete AWS_ACCESS_KEY_ID
```

---

## Terraform Output Wiring

### Output Wiring Script

**backend/scripts/load-terraform-outputs.sh:**

```bash
#!/bin/sh
# ==============================================================================
# Load Terraform Outputs Script
# ==============================================================================
# Reads Terraform output JSON and exports environment variables for application
# ==============================================================================

TERRAFORM_OUTPUTS="/terraform/outputs.json"

if [ ! -f "$TERRAFORM_OUTPUTS" ]; then
  echo "ERROR: Terraform outputs file not found at $TERRAFORM_OUTPUTS"
  exit 1
fi

# Parse JSON and export environment variables
export RDS_ENDPOINT=$(jq -r '.rds_endpoint.value' "$TERRAFORM_OUTPUTS")
export RDS_READER_ENDPOINT=$(jq -r '.rds_reader_endpoint.value // ""' "$TERRAFORM_OUTPUTS")
export RDS_DB_NAME=$(jq -r '.rds_db_name.value' "$TERRAFORM_OUTPUTS")
export RDS_USERNAME=$(jq -r '.rds_username.value' "$TERRAFORM_OUTPUTS")

export S3_BUCKET_DOCUMENTS=$(jq -r '.s3_bucket_documents.value' "$TERRAFORM_OUTPUTS")
export S3_BUCKET_BACKUPS=$(jq -r '.s3_bucket_backups.value' "$TERRAFORM_OUTPUTS")
export S3_BUCKET_AUDIT_LOGS=$(jq -r '.s3_bucket_audit_logs.value' "$TERRAFORM_OUTPUTS")

export KMS_MASTER_KEY_ID=$(jq -r '.kms_master_key_id.value' "$TERRAFORM_OUTPUTS")
export KMS_MASTER_KEY_ARN=$(jq -r '.kms_master_key_arn.value' "$TERRAFORM_OUTPUTS")

export VPC_ID=$(jq -r '.vpc_id.value' "$TERRAFORM_OUTPUTS")
export APP_IAM_ROLE_ARN=$(jq -r '.app_iam_role_arn.value' "$TERRAFORM_OUTPUTS")
export AWS_REGION=$(jq -r '.aws_region.value' "$TERRAFORM_OUTPUTS")

# Construct DATABASE_URL from RDS outputs
# Assumes RDS_PASSWORD is provided via Railway environment variable
export DATABASE_URL="postgresql+asyncpg://${RDS_USERNAME}:${RDS_PASSWORD}@${RDS_ENDPOINT}/${RDS_DB_NAME}"

echo "Terraform outputs loaded:"
echo "  - RDS Endpoint: $RDS_ENDPOINT"
echo "  - S3 Documents Bucket: $S3_BUCKET_DOCUMENTS"
echo "  - KMS Master Key: $KMS_MASTER_KEY_ID"
echo "  - VPC ID: $VPC_ID"
```

### Updated Startup Script

**backend/scripts/startup.sh:**

```bash
#!/bin/sh
set -e

echo "=========================================="
echo "HIPAA-Compliant Backend API - Starting"
echo "=========================================="

# ------------------------------------------------------------------------------
# Load Terraform Outputs
# ------------------------------------------------------------------------------
echo ""
echo "[0/3] Loading Terraform infrastructure outputs..."

if [ -f "/terraform/outputs.json" ]; then
  source /backend/scripts/load-terraform-outputs.sh
  echo "✓ Terraform outputs loaded successfully"
else
  echo "⚠ WARNING: Terraform outputs not found. Using environment variables directly."
fi

# ------------------------------------------------------------------------------
# Database Migrations
# ------------------------------------------------------------------------------
echo ""
echo "[1/3] Running database migrations..."
alembic upgrade head
echo "✓ Database migrations completed successfully"

# ------------------------------------------------------------------------------
# Application Startup
# ------------------------------------------------------------------------------
echo ""
echo "[2/3] Starting application server..."
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips '*'
```

---

## Deployment Workflow

### Initial Deployment

**Step 1: Prepare Repository**
```bash
# Ensure all Terraform code is committed
git add terraform/
git commit -m "Add Terraform infrastructure configuration"
git push origin main
```

**Step 2: Set Railway Environment Variables**
```bash
# Set required environment variables in Railway dashboard
# See "Required Railway Environment Variables" section above
```

**Step 3: Deploy Terraform Service**
```bash
# Railway automatically deploys Terraform service on git push
# Monitor deployment logs:
railway logs --service terraform

# Expected output:
# Initializing Terraform...
# Applying infrastructure changes...
# Apply complete! Resources: 47 added, 0 changed, 0 destroyed.
# Terraform outputs exported to /app/outputs.json
```

**Step 4: Deploy Backend Service**
```bash
# Railway automatically deploys backend service after Terraform completes
railway logs --service backend

# Expected output:
# [0/3] Loading Terraform infrastructure outputs...
# ✓ Terraform outputs loaded successfully
# [1/3] Running database migrations...
# ✓ Database migrations completed successfully
# [2/3] Starting application server...
# INFO:     Started server process [1]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

**Step 5: Verify Deployment**
```bash
# Get Railway deployment URL
railway domain

# Test health endpoint
curl https://your-railway-domain.railway.app/api/v1/health/ready

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "s3": "accessible",
#   "kms": "accessible"
# }
```

---

### Update Deployment

**Step 1: Make Infrastructure Changes**
```bash
# Edit Terraform configuration
vi terraform/modules/rds/main.tf

# Commit changes
git add terraform/
git commit -m "Scale RDS instance to db.r6g.2xlarge"
git push origin main
```

**Step 2: Railway Redeploys Automatically**
```bash
# Monitor Terraform service logs
railway logs --service terraform --follow

# Terraform will:
# 1. Detect infrastructure drift
# 2. Plan changes
# 3. Apply changes automatically
# 4. Export updated outputs.json
```

**Step 3: Backend Service Restarts (If Needed)**
```bash
# If infrastructure changes require backend restart:
railway restart --service backend

# Backend will reload updated Terraform outputs
```

---

### Rollback Deployment

**Step 1: Revert Git Commit**
```bash
git revert <commit-hash>
git push origin main
```

**Step 2: Railway Redeploys Previous Version**
```bash
# Railway automatically deploys reverted commit
railway logs --service terraform --follow

# Terraform will restore previous infrastructure state
```

---

## Troubleshooting

### Issue: Terraform Apply Fails in Railway

**Symptoms:**
```
Error: Error creating RDS instance: DBInstanceAlreadyExists
```

**Solution:**
```bash
# Option 1: Import existing resource
railway run --service terraform terraform import module.rds.aws_db_instance.main hipaa-db-production

# Option 2: Destroy and recreate (dangerous - data loss)
railway run --service terraform terraform destroy -auto-approve
railway restart --service terraform
```

---

### Issue: Backend Cannot Connect to RDS

**Symptoms:**
```
ERROR: could not connect to server: Connection timed out
```

**Solution:**
```bash
# 1. Verify Terraform outputs loaded
railway logs --service backend | grep "Terraform outputs loaded"

# 2. Verify DATABASE_URL constructed correctly
railway run --service backend env | grep DATABASE_URL

# 3. Verify RDS endpoint is accessible (requires VPN or bastion host)
# RDS is in private subnet, not directly accessible from internet

# 4. Check security group rules allow Railway IP ranges
terraform workspace select production
terraform output | grep security_group
```

---

### Issue: S3 Access Denied

**Symptoms:**
```
ERROR: An error occurred (AccessDenied) when calling the PutObject operation
```

**Solution:**
```bash
# 1. Verify IAM role permissions
aws iam get-role-policy \
  --role-name hipaa-app-backend-production \
  --policy-name production-s3-access-policy

# 2. Verify AWS credentials are set in Railway
railway variables | grep AWS_ACCESS_KEY_ID

# 3. Verify KMS key access
aws kms get-key-policy \
  --key-id $(railway run --service backend env | grep KMS_MASTER_KEY_ID | cut -d= -f2) \
  --policy-name default

# 4. Test S3 access directly
railway run --service backend aws s3 ls s3://$(railway run --service backend env | grep S3_BUCKET_DOCUMENTS | cut -d= -f2)
```

---

### Issue: Terraform State Locked

**Symptoms:**
```
Error: Error acquiring the state lock
```

**Solution:**
```bash
# 1. Check DynamoDB for lock
aws dynamodb scan --table-name terraform-state-lock

# 2. If lock is stale (previous deployment crashed), force unlock
railway run --service terraform terraform force-unlock <lock-id>

# 3. Retry deployment
railway restart --service terraform
```

---

## Alternative Deployment Options

### Option 1: Local Terraform, Railway Backend

**Use Case:** Prefer to manage infrastructure locally, deploy application on Railway.

**Workflow:**
```bash
# 1. Run Terraform locally
cd terraform
terraform workspace select production
terraform apply -var-file="terraform.tfvars.production"

# 2. Export outputs to Railway
terraform output -json > outputs.json

# 3. Manually set Railway environment variables
terraform output -json | jq -r 'to_entries | .[] | "\(.key)=\(.value.value)"' | \
  xargs -I {} railway variables set {}

# 4. Deploy backend only on Railway
railway up --service backend
```

---

### Option 2: CI/CD Pipeline (GitHub Actions)

**Use Case:** Automated deployment on git push with approval gates.

**Workflow:**
```yaml
# .github/workflows/deploy-railway.yml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: hashicorp/setup-terraform@v2

      - name: Terraform Init
        run: terraform init
        working-directory: terraform

      - name: Terraform Apply
        run: terraform apply -var-file="terraform.tfvars.production" -auto-approve
        working-directory: terraform
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Export Outputs
        run: terraform output -json > outputs.json
        working-directory: terraform

      - name: Deploy to Railway
        run: railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

---

## Best Practices

### Security

1. **Never commit credentials to Git:** Use Railway environment variables
2. **Use IAM roles instead of access keys:** Where possible, use OIDC or IAM roles
3. **Rotate credentials regularly:** AWS access keys every 90 days
4. **Use secrets manager:** Store RDS password in AWS Secrets Manager, reference in Railway

### Reliability

1. **Enable health checks:** Railway health check verifies backend is responding
2. **Set restart policy:** Restart on failure with max retries
3. **Monitor logs:** Use Railway logs to detect issues early
4. **Test in dev/staging first:** Never deploy directly to production

### Cost Optimization

1. **Stop dev environments:** Use Railway's sleep feature for dev instances
2. **Monitor Railway costs:** Railway charges per GB-hour of compute
3. **Optimize Terraform service:** Only run when infrastructure changes (not on every deploy)

---

## Support Resources

- **Railway Documentation:** https://docs.railway.app/
- **Railway Community:** https://help.railway.app/
- **Railway Status:** https://status.railway.app/
- **Terraform Railway Provider:** N/A (use CLI or API)

---

## Summary

**Key Integration Points:**
1. Terraform service provisions AWS infrastructure
2. `outputs.json` bridges Terraform and Railway
3. Startup script loads outputs into environment variables
4. Backend connects to AWS using environment variables

**Deployment Flow:**
```
Git Push → Railway Build → Terraform Apply → Export Outputs → Backend Start → Health Check
```

**Verification Checklist:**
- [ ] Terraform service deploys successfully
- [ ] Backend service starts without errors
- [ ] Health check endpoint returns 200 OK
- [ ] Application can connect to RDS
- [ ] Application can read/write to S3
- [ ] Application can encrypt/decrypt with KMS
