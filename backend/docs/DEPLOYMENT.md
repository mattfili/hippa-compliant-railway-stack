# Deployment Guide

This guide provides step-by-step instructions for deploying the HIPAA-compliant backend API to Railway with AWS infrastructure integration.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Railway Deployment](#railway-deployment)
- [AWS Secrets Manager Setup](#aws-secrets-manager-setup)
- [Environment Variables Reference](#environment-variables-reference)
- [Health Check Configuration](#health-check-configuration)
- [Database Migrations](#database-migrations)
- [Monitoring & Logging](#monitoring--logging)
- [Rollback Procedures](#rollback-procedures)
- [Troubleshooting](#troubleshooting)

## Overview

The application deployment architecture:

```
GitHub Repository
    ↓ (automatic deployment)
Railway Platform
    ├── Backend API Service (Docker container)
    │   ├── Automatic migrations (Alembic)
    │   ├── Health checks (/api/v1/health/ready)
    │   └── Structured logs → CloudWatch
    │
    ├── PostgreSQL Database
    │   └── Automatic DATABASE_URL injection
    │
    └── Environment Variables
        ├── Railway-managed (DATABASE_URL)
        └── User-configured (see table below)

AWS Services
    ├── Secrets Manager (OIDC_CLIENT_SECRET, API keys)
    ├── IAM (Railway service role)
    └── CloudWatch (centralized logging)
```

### Deployment Flow

1. **Code Push**: Developer pushes to GitHub
2. **Build**: Railway detects changes, builds Docker image
3. **Migrations**: Startup script runs `alembic upgrade head`
4. **Start**: Uvicorn starts FastAPI application
5. **Health Check**: Railway pings `/api/v1/health/ready`
6. **Traffic**: Railway routes traffic to healthy containers

## Prerequisites

Before deploying, ensure you have:

### Required Accounts & Services

- **Railway Account** with HIPAA BAA signed
  - Sign up: https://railway.app
  - Contact Railway support for BAA: support@railway.app

- **AWS Account** with BAA signed
  - Ensure BAA covers: RDS, S3, KMS, Secrets Manager, CloudWatch
  - Verify BAA status: AWS Console → Artifact → Agreements

- **GitHub Account** with repository access
  - Fork or clone this repository
  - Configure deploy keys if private repository

- **Identity Provider** (AWS Cognito, Okta, Auth0, or Azure AD)
  - IdP must have BAA signed
  - OIDC/SAML configured with custom tenant claim
  - See [AUTH_CONFIGURATION.md](AUTH_CONFIGURATION.md)

### Required CLI Tools

```bash
# Railway CLI
npm install -g @railway/cli

# AWS CLI
pip install awscli
aws configure

# Optional: Docker for local testing
docker --version
```

### Required Permissions

- **Railway**: Admin access to Railway project
- **AWS**: IAM permissions to create secrets, roles, and policies
- **GitHub**: Push access to repository

## Railway Deployment

### Step 1: Fork Repository

```bash
# Fork repository on GitHub (via web UI)
# Then clone your fork
git clone https://github.com/your-username/hipaa-compliant-railway-stack.git
cd hipaa-compliant-railway-stack/backend
```

### Step 2: Create Railway Project

**Option A: Via Railway CLI**

```bash
# Login to Railway
railway login

# Initialize new project
railway init

# Link to Railway project
railway link
```

**Option B: Via Railway Dashboard**

1. Navigate to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your forked repository
4. Choose `backend` as root directory

### Step 3: Add PostgreSQL Service

**Via Railway Dashboard**:

1. Open your Railway project
2. Click "+ New" → "Database" → "Add PostgreSQL"
3. Railway automatically:
   - Provisions PostgreSQL instance
   - Injects `DATABASE_URL` environment variable
   - Configures networking

**Via Railway CLI**:

```bash
# Add PostgreSQL service
railway add --database postgres
```

**Verify DATABASE_URL**:

```bash
# Check environment variables
railway variables

# Should see DATABASE_URL with postgresql:// format
```

### Step 4: Configure Environment Variables

Set required environment variables in Railway dashboard or CLI:

**Via Dashboard**:

1. Project → Settings → Variables
2. Add each variable from table below

**Via CLI**:

```bash
# Set environment variables
railway variables set ENVIRONMENT=production
railway variables set LOG_LEVEL=INFO
railway variables set ALLOWED_ORIGINS=https://your-app.com
railway variables set OIDC_ISSUER_URL=https://your-idp.example.com
railway variables set OIDC_CLIENT_ID=your_client_id
railway variables set JWT_TENANT_CLAIM_NAME=tenant_id
railway variables set JWT_MAX_LIFETIME_MINUTES=60
railway variables set AWS_REGION=us-east-1
railway variables set AWS_SECRETS_MANAGER_SECRET_ID=hipaa-template/prod/secrets
```

See [Environment Variables Reference](#environment-variables-reference) for complete list.

### Step 5: Deploy Application

**Automatic Deployment** (recommended):

1. Railway watches GitHub repository
2. Push to main branch triggers deployment
3. Railway builds Docker image
4. Runs startup script with migrations
5. Performs health checks
6. Routes traffic to healthy containers

```bash
# Push changes to trigger deployment
git add .
git commit -m "Initial deployment"
git push origin main
```

**Manual Deployment**:

```bash
# Deploy current directory
railway up

# Or deploy specific service
railway up --service backend-api
```

### Step 6: Monitor Deployment

**Check Build Logs**:

```bash
# Follow build logs
railway logs --follow

# Or view in dashboard
# Project → Deployments → Click deployment → View logs
```

**Verify Deployment Success**:

```bash
# Check service status
railway status

# Test health endpoints
curl https://your-app.railway.app/api/v1/health/live
curl https://your-app.railway.app/api/v1/health/ready
```

**Expected Health Check Response**:

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "secrets": "ok"
  },
  "timestamp": 1698765432
}
```

### Step 7: Configure Custom Domain (Optional)

**Via Dashboard**:

1. Project → Settings → Domains
2. Click "Generate Domain" (gets railway.app subdomain)
3. Or "Custom Domain" to use your own domain
4. Add DNS records as instructed

**Via CLI**:

```bash
# Generate railway.app domain
railway domain

# Add custom domain
railway domain add your-app.example.com
```

Update ALLOWED_ORIGINS and IdP callback URLs with new domain.

## AWS Secrets Manager Setup

Store sensitive secrets in AWS Secrets Manager instead of environment variables.

### Step 1: Create Secret

```bash
# Create secret with OIDC client secret
aws secretsmanager create-secret \
  --name hipaa-template/prod/secrets \
  --description "Production secrets for HIPAA-compliant backend" \
  --secret-string '{
    "OIDC_CLIENT_SECRET": "your-cognito-client-secret-here"
  }' \
  --region us-east-1
```

**Or via AWS Console**:

1. Navigate to AWS Secrets Manager → Secrets → Store a new secret
2. Select "Other type of secret"
3. Key/value pairs:
   - Key: `OIDC_CLIENT_SECRET`
   - Value: Your IdP client secret
4. Secret name: `hipaa-template/prod/secrets`
5. Description: "Production secrets for HIPAA-compliant backend"
6. Leave rotation disabled (manual rotation recommended)

### Step 2: Create IAM Policy

```bash
# Create policy JSON file
cat > railway-secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:hipaa-template/prod/secrets*"
    }
  ]
}
EOF

# Create IAM policy
aws iam create-policy \
  --policy-name RailwaySecretsAccess \
  --policy-document file://railway-secrets-policy.json \
  --description "Allow Railway to access Secrets Manager"
```

### Step 3: Create IAM Role for Railway

```bash
# Create trust policy for Railway
cat > railway-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create IAM role
aws iam create-role \
  --role-name RailwayBackendService \
  --assume-role-policy-document file://railway-trust-policy.json \
  --description "Role for Railway backend service"

# Attach secrets policy to role
aws iam attach-role-policy \
  --role-name RailwayBackendService \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/RailwaySecretsAccess
```

### Step 4: Configure Railway with AWS Credentials

**Option A: Environment Variables** (for Railway without IRSA):

```bash
# Create IAM user for Railway
aws iam create-user --user-name railway-backend-user

# Attach policy to user
aws iam attach-user-policy \
  --user-name railway-backend-user \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/RailwaySecretsAccess

# Create access keys
aws iam create-access-key --user-name railway-backend-user

# Set in Railway environment variables
railway variables set AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
railway variables set AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Option B: Instance Profile** (if Railway supports IAM roles):

Consult Railway documentation for attaching IAM roles to services.

### Step 5: Verify Secrets Access

```bash
# SSH into Railway container or check logs
railway run bash

# Test AWS credentials
aws sts get-caller-identity

# Test secret access
aws secretsmanager get-secret-value \
  --secret-id hipaa-template/prod/secrets \
  --region us-east-1
```

Check application logs for secret loading:

```bash
railway logs | grep "Secrets Manager"
# Should see: "Successfully loaded secrets from AWS Secrets Manager"
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example | Source |
|----------|-------------|---------|--------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://user:pass@...` | Auto-injected by Railway |
| `ENVIRONMENT` | Application environment | `production` | User-configured |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `https://app.example.com` | User-configured |
| `OIDC_ISSUER_URL` | Identity provider issuer URL | `https://cognito-idp...` | User-configured |
| `OIDC_CLIENT_ID` | OAuth client ID | `7abcdefghijklmn` | User-configured |
| `AWS_REGION` | AWS region for services | `us-east-1` | User-configured |
| `AWS_SECRETS_MANAGER_SECRET_ID` | Secret ID for runtime secrets | `hipaa-template/prod/secrets` | User-configured |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `JWT_TENANT_CLAIM_NAME` | JWT claim name for tenant ID | `tenant_id` | `organization_id`, `custom:tenant_id` |
| `JWT_MAX_LIFETIME_MINUTES` | Maximum token lifetime (minutes) | `60` | `30`, `60`, `120` |
| `JWKS_CACHE_TTL_SECONDS` | JWKS cache duration (seconds) | `3600` | `1800`, `3600`, `7200` |

### Sensitive Variables (Store in Secrets Manager)

| Variable | Description | Storage |
|----------|-------------|---------|
| `OIDC_CLIENT_SECRET` | OAuth client secret | AWS Secrets Manager |
| `DATABASE_PASSWORD` | Database password (if not using DATABASE_URL) | Railway-managed |

See [RAILWAY_ENV.md](RAILWAY_ENV.md) for detailed variable documentation.

## Health Check Configuration

Railway uses health checks to determine if a deployment is successful.

### Health Check Endpoints

**Liveness Probe** (`/api/v1/health/live`):
- Indicates if application is running
- Always returns 200 OK unless crashed
- Fast response (< 100ms)
- No external dependency checks

**Readiness Probe** (`/api/v1/health/ready`):
- Indicates if application can serve traffic
- Validates database connectivity
- Checks AWS Secrets Manager (optional)
- Returns 503 if dependencies unavailable

### Railway Configuration

In `backend/railway.json`:

```json
{
  "deploy": {
    "healthcheckPath": "/api/v1/health/ready",
    "healthcheckTimeout": 30
  }
}
```

Railway will:
1. Wait up to 30 seconds for first successful health check
2. Perform health check every 10 seconds
3. Mark deployment failed if health check never succeeds
4. Route traffic only to healthy containers

### Customizing Health Checks

Edit `backend/railway.json`:

```json
{
  "deploy": {
    "healthcheckPath": "/api/v1/health/live",  // Use liveness for faster checks
    "healthcheckTimeout": 60,                   // Increase timeout for slow starts
    "healthcheckInterval": 30                   // Check every 30 seconds
  }
}
```

## Database Migrations

Migrations run automatically during deployment via startup script.

### Automatic Migration Flow

1. Container starts
2. Startup script runs: `scripts/startup.sh`
3. Script executes: `alembic upgrade head`
4. Application starts: `uvicorn app.main:app`

### Manual Migration Execution

**Run migrations via Railway CLI**:

```bash
# Run command in Railway environment
railway run alembic upgrade head

# Or SSH into container
railway run bash
alembic upgrade head
```

**Run migrations locally against Railway database**:

```bash
# Get DATABASE_URL from Railway
railway variables get DATABASE_URL

# Set locally
export DATABASE_URL="postgresql://..."

# Run migrations
alembic upgrade head
```

### Create New Migrations

```bash
# Create migration for new changes
alembic revision -m "add_users_table"

# Edit generated migration file
# backend/alembic/versions/TIMESTAMP_add_users_table.py

# Test locally
alembic upgrade head

# Commit and push to trigger deployment
git add alembic/versions/
git commit -m "Add users table migration"
git push origin main
```

### Migration Best Practices

1. **Test Locally First**: Always test migrations on local database
2. **Idempotent Operations**: Use `IF NOT EXISTS` for table/column creation
3. **Backward Compatible**: Ensure migrations don't break running code
4. **Reversible**: Implement `downgrade()` function
5. **Data Migrations**: Separate schema and data migrations
6. **Backup First**: Backup production database before major migrations

### Rollback Migration

```bash
# Rollback one migration
railway run alembic downgrade -1

# Rollback to specific revision
railway run alembic downgrade <revision_id>

# View migration history
railway run alembic history
```

## Monitoring & Logging

### Railway Logs

**View Logs**:

```bash
# Follow logs in real-time
railway logs --follow

# View last 100 lines
railway logs --tail 100

# Filter by timestamp
railway logs --since 1h

# Filter by service
railway logs --service backend-api
```

**Via Dashboard**:
- Project → Deployments → Click deployment → View logs
- Real-time log streaming with search

### CloudWatch Integration

Railway automatically ships logs to CloudWatch (if configured).

**Access CloudWatch Logs**:

1. AWS Console → CloudWatch → Log groups
2. Find log group: `/railway/backend-api`
3. Use CloudWatch Insights for queries

**CloudWatch Insights Queries**:

```sql
-- Find errors in last hour
fields @timestamp, @message, level, error_code
| filter level = "ERROR"
| sort @timestamp desc
| limit 100

-- Find requests for specific tenant
fields @timestamp, @message, tenant_id, request_id
| filter tenant_id = "org-123"
| sort @timestamp desc

-- Find slow requests (> 1 second)
fields @timestamp, @message, duration_ms
| filter duration_ms > 1000
| sort duration_ms desc
```

### Metrics & Alerts

**Railway Metrics** (dashboard):
- CPU usage
- Memory usage
- Request rate
- Response time
- Error rate

**CloudWatch Alarms**:

```bash
# Create alarm for high error rate
aws cloudwatch put-metric-alarm \
  --alarm-name backend-high-error-rate \
  --alarm-description "Alert when error rate exceeds 5%" \
  --metric-name ErrorRate \
  --namespace Railway/Backend \
  --statistic Average \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:alert-topic
```

## Rollback Procedures

### Rollback to Previous Deployment

**Via Railway Dashboard**:

1. Project → Deployments
2. Find previous successful deployment
3. Click "Redeploy"

**Via Railway CLI**:

```bash
# List deployments
railway deployments list

# Rollback to specific deployment
railway rollback <deployment-id>
```

### Rollback Database Migration

```bash
# Identify current migration
railway run alembic current

# Rollback one migration
railway run alembic downgrade -1

# Verify rollback
railway run alembic current

# Restart application
railway service restart
```

### Emergency Rollback Checklist

1. **Identify Issue**: Check logs, metrics, error rates
2. **Stop Deployment**: Cancel ongoing deployment if needed
3. **Rollback Code**: Redeploy previous version
4. **Rollback Database**: If migration caused issue
5. **Verify Fix**: Check health endpoints, test critical paths
6. **Notify Team**: Update status page, notify stakeholders
7. **Post-Mortem**: Document issue and prevention steps

## Troubleshooting

### Deployment Fails

**Symptoms**: Deployment shows "Failed" status in Railway

**Diagnosis**:

```bash
# Check build logs
railway logs --deployment <deployment-id>

# Look for errors in build stage
grep -i "error" logs.txt
```

**Common Causes**:

1. **Docker build fails**: Missing dependencies, syntax errors
   - Fix: Review Dockerfile, test build locally

2. **Migration fails**: Database schema conflict
   - Fix: Rollback migration, fix conflicts, redeploy

3. **Health check timeout**: Application not starting in time
   - Fix: Increase health check timeout, optimize startup

### Database Connection Fails

**Symptoms**: `SYS_001: Database unreachable` errors

**Diagnosis**:

```bash
# Check DATABASE_URL
railway variables get DATABASE_URL

# Test connection
railway run psql $DATABASE_URL -c "SELECT 1"

# Check database status
railway service status postgres
```

**Resolution**:
1. Verify DATABASE_URL format correct
2. Restart database service if needed
3. Check network connectivity
4. Review connection pool settings

### Secrets Manager Fails

**Symptoms**: `SYS_002: Secrets Manager unavailable` errors

**Diagnosis**:

```bash
# Check AWS credentials
railway run aws sts get-caller-identity

# Test secret access
railway run aws secretsmanager get-secret-value \
  --secret-id hipaa-template/prod/secrets
```

**Resolution**:
1. Verify IAM permissions
2. Check AWS region correct
3. Confirm secret exists
4. Review AWS service health

### High Memory Usage

**Symptoms**: Container restarts, OOM errors

**Diagnosis**:

```bash
# Check resource usage
railway metrics

# Review memory consumption in logs
railway logs | grep "memory"
```

**Resolution**:
1. Increase memory limit in Railway settings
2. Optimize connection pool size
3. Review for memory leaks
4. Enable memory profiling

### Slow Performance

**Symptoms**: High response times, timeouts

**Diagnosis**:

```bash
# Check response times in logs
railway logs | grep "duration_ms"

# Review database query performance
# Enable SQL logging temporarily
```

**Resolution**:
1. Optimize database queries
2. Add database indexes
3. Increase connection pool size
4. Enable caching (future feature)

## Additional Resources

- **Railway Documentation**: https://docs.railway.app
- **AWS Secrets Manager**: https://docs.aws.amazon.com/secretsmanager/
- **Alembic Migrations**: https://alembic.sqlalchemy.org
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/

## Support

For deployment issues:

1. Check Railway status: https://status.railway.app
2. Review Railway docs: https://docs.railway.app
3. Railway Discord: https://discord.gg/railway
4. AWS Support (if BAA issues)
5. Project issues: GitHub repository issues

## Next Steps

After successful deployment:

1. Configure monitoring and alerts
2. Set up log aggregation
3. Test authentication flow end-to-end
4. Perform security audit
5. Document runbooks for common issues
6. Schedule regular backups
7. Plan for scaling and high availability

See [HIPAA_READINESS.md](HIPAA_READINESS.md) for compliance verification checklist.
