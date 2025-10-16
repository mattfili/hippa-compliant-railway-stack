# Railway Environment Variables

This document provides a comprehensive reference for all environment variables used in the HIPAA-compliant backend API when deployed on Railway.

## Table of Contents

- [Overview](#overview)
- [Variable Categories](#variable-categories)
- [Required Variables](#required-variables)
- [Optional Variables](#optional-variables)
- [Auto-Injected Variables](#auto-injected-variables)
- [AWS Configuration](#aws-configuration)
- [Authentication Configuration](#authentication-configuration)
- [Application Configuration](#application-configuration)
- [Sensitive Variables](#sensitive-variables)
- [Environment-Specific Examples](#environment-specific-examples)
- [Verification](#verification)

## Overview

Environment variables configure the application for different deployment environments (development, staging, production). Variables are loaded from:

1. **Railway Environment Variables** - Set in Railway dashboard or CLI
2. **AWS Secrets Manager** - Sensitive secrets fetched at runtime
3. **Railway Service Linking** - Auto-injected by Railway (e.g., DATABASE_URL)

### Variable Loading Priority

1. Railway environment variables (highest priority)
2. AWS Secrets Manager (for sensitive values)
3. Default values in application code (lowest priority)

## Variable Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| **Application** | Core application settings | `ENVIRONMENT`, `LOG_LEVEL` |
| **Database** | Database connection | `DATABASE_URL` |
| **CORS** | Cross-origin configuration | `ALLOWED_ORIGINS` |
| **Authentication** | IdP and JWT settings | `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID` |
| **AWS** | AWS service configuration | `AWS_REGION`, `AWS_SECRETS_MANAGER_SECRET_ID` |
| **Advanced** | Optional tuning parameters | `JWKS_CACHE_TTL_SECONDS` |

## Required Variables

These variables MUST be set for the application to function correctly.

### DATABASE_URL

**Description**: PostgreSQL database connection URL

**Format**: `postgresql://username:password@host:port/database` or `postgresql+asyncpg://...`

**Source**: Auto-injected by Railway when PostgreSQL service is linked

**Example**:
```
DATABASE_URL=postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway
```

**Notes**:
- Railway automatically injects this when you add PostgreSQL service
- Application converts `postgresql://` to `postgresql+asyncpg://` for async support
- Do not set manually unless using external database

**Verification**:
```bash
# Check if set
railway variables get DATABASE_URL

# Test connection
railway run psql $DATABASE_URL -c "SELECT 1"
```

---

### ENVIRONMENT

**Description**: Application environment name

**Required**: Yes

**Valid Values**: `development`, `staging`, `production`

**Default**: None (must be explicitly set)

**Example**:
```
ENVIRONMENT=production
```

**Impact**:
- Controls logging format (JSON in production, simple in development)
- Enables/disables debug features
- Affects error response detail level
- Determines secret loading behavior

**Verification**:
```bash
railway variables get ENVIRONMENT
```

---

### ALLOWED_ORIGINS

**Description**: Comma-separated list of allowed CORS origins

**Required**: Yes

**Format**: `https://domain1.com,https://domain2.com`

**Example**:
```
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
```

**Security Notes**:
- Must use explicit origins (no wildcards with credentials)
- Use HTTPS in production
- Include all frontend domains that need API access
- Localhost origins only for development

**Common Values**:
- Development: `http://localhost:3000,http://localhost:5173`
- Production: `https://app.example.com`

**Verification**:
```bash
# Test CORS headers
curl -v -H "Origin: https://app.example.com" \
  https://your-app.railway.app/api/v1/health/live
```

---

### OIDC_ISSUER_URL

**Description**: Identity provider's OIDC issuer URL

**Required**: Yes (for authentication features)

**Format**: `https://idp.example.com` or `https://cognito-idp.{region}.amazonaws.com/{user_pool_id}`

**Examples**:
- AWS Cognito: `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123`
- Okta: `https://your-domain.okta.com/oauth2/default`
- Auth0: `https://your-tenant.auth0.com/`
- Azure AD: `https://login.microsoftonline.com/{tenant-id}/v2.0`

**Notes**:
- Must be publicly accessible HTTPS URL
- Application fetches JWKS keys from `{OIDC_ISSUER_URL}/.well-known/jwks.json`
- Used to validate JWT token `iss` claim

**Verification**:
```bash
# Verify JWKS endpoint accessible
curl https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123/.well-known/jwks.json
```

---

### OIDC_CLIENT_ID

**Description**: OAuth/OIDC application client ID

**Required**: Yes (for authentication features)

**Format**: Alphanumeric string (length varies by provider)

**Example**:
```
OIDC_CLIENT_ID=7abcdefghijklmnopqrstuv
```

**Notes**:
- Public identifier (not secret)
- Obtained when creating application in IdP
- Used to validate JWT token `aud` claim

**Where to Find**:
- AWS Cognito: User Pool → App clients → Client ID
- Okta: Applications → Your App → Client ID
- Auth0: Applications → Your App → Client ID
- Azure AD: App registrations → Your App → Application (client) ID

**Verification**:
```bash
railway variables get OIDC_CLIENT_ID
```

---

### AWS_REGION

**Description**: AWS region for AWS services

**Required**: Yes (when using AWS Secrets Manager)

**Format**: AWS region code

**Valid Values**: `us-east-1`, `us-west-2`, `eu-west-1`, etc.

**Example**:
```
AWS_REGION=us-east-1
```

**Notes**:
- Must match region where secrets are stored
- Must match region for other AWS services (RDS, S3)
- Use same region for all services to minimize latency

**Verification**:
```bash
railway variables get AWS_REGION
```

---

### AWS_SECRETS_MANAGER_SECRET_ID

**Description**: ARN or name of secret in AWS Secrets Manager

**Required**: Yes (for production)

**Format**: Secret name or full ARN

**Examples**:
- Name: `hipaa-template/prod/secrets`
- ARN: `arn:aws:secretsmanager:us-east-1:123456789012:secret:hipaa-template/prod/secrets-AbCdEf`

**Example**:
```
AWS_SECRETS_MANAGER_SECRET_ID=hipaa-template/prod/secrets
```

**Notes**:
- Can be empty for local development (graceful fallback)
- Secret must exist in specified AWS region
- IAM permissions required to read secret

**Secret Contents**:
```json
{
  "OIDC_CLIENT_SECRET": "your-oauth-client-secret"
}
```

**Verification**:
```bash
# Check secret exists
aws secretsmanager describe-secret \
  --secret-id hipaa-template/prod/secrets

# Test secret access
railway run aws secretsmanager get-secret-value \
  --secret-id hipaa-template/prod/secrets
```

---

## Optional Variables

These variables have sensible defaults but can be customized.

### LOG_LEVEL

**Description**: Logging verbosity level

**Required**: No

**Default**: `INFO`

**Valid Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Example**:
```
LOG_LEVEL=INFO
```

**Recommendations**:
- Development: `DEBUG` (verbose logging)
- Staging: `INFO` (normal logging)
- Production: `INFO` or `WARNING` (minimal logging)

**Impact**:
- `DEBUG`: All logs including request/response details
- `INFO`: Normal operation logs (requests, auth events)
- `WARNING`: Only warnings and errors
- `ERROR`: Only errors and critical issues

**Verification**:
```bash
# Check log output
railway logs | grep -i "level"
```

---

### JWT_TENANT_CLAIM_NAME

**Description**: Name of JWT claim containing tenant identifier

**Required**: No

**Default**: `tenant_id`

**Valid Values**: Any string (common: `tenant_id`, `organization_id`, `org_id`, `custom:tenant_id`)

**Example**:
```
JWT_TENANT_CLAIM_NAME=tenant_id
```

**Use Cases**:
- AWS Cognito custom attributes: `custom:tenant_id`
- Okta custom claims: `organization_id`
- Auth0 namespaced claims: `https://your-app.com/tenant_id`

**Notes**:
- Must match claim name in JWT tokens from IdP
- See [AUTH_CONFIGURATION.md](AUTH_CONFIGURATION.md) for IdP setup

**Verification**:
```bash
# Decode JWT and check claim name
jwt decode $TOKEN | jq '.payload.tenant_id'
```

---

### JWT_MAX_LIFETIME_MINUTES

**Description**: Maximum allowed JWT token lifetime in minutes

**Required**: No

**Default**: `60`

**Valid Values**: Integer (recommended: 15-120 for HIPAA compliance)

**Example**:
```
JWT_MAX_LIFETIME_MINUTES=60
```

**HIPAA Recommendations**:
- Standard access: 60 minutes
- High-security clinical apps: 15-30 minutes
- Administrative apps: up to 120 minutes
- Never exceed 240 minutes for PHI access

**Notes**:
- Application rejects tokens with lifetime exceeding this value
- Calculated as `(exp - iat)` from JWT claims
- IdP must issue tokens within this limit

**Verification**:
```bash
# Check token lifetime
jwt decode $TOKEN | jq '{iat, exp, lifetime: (.exp - .iat) / 60}'
```

---

### JWKS_CACHE_TTL_SECONDS

**Description**: How long to cache JWKS keys from IdP

**Required**: No

**Default**: `3600` (1 hour)

**Valid Values**: Integer seconds (recommended: 1800-7200)

**Example**:
```
JWKS_CACHE_TTL_SECONDS=3600
```

**Trade-offs**:
- **Shorter TTL**: Faster key rotation detection, more IdP API calls
- **Longer TTL**: Fewer API calls, slower key rotation detection

**Recommendations**:
- Development: `600` (10 minutes) - for testing key rotation
- Production: `3600` (1 hour) - balance between freshness and API calls

**Notes**:
- Cache refreshes automatically before expiration
- Failed JWKS fetches don't clear cache (uses stale keys)
- Restart application to force cache refresh

**Verification**:
```bash
# Check logs for JWKS fetches
railway logs | grep "JWKS"
```

---

## Auto-Injected Variables

These variables are automatically set by Railway.

### DATABASE_URL

**Description**: PostgreSQL connection URL

**Source**: Auto-injected when PostgreSQL service is linked

**Format**: `postgresql://user:pass@host:port/database`

**Notes**:
- Do NOT set manually
- Automatically updated if database service changes
- Application converts to `postgresql+asyncpg://` for async support

---

### PORT

**Description**: Port number for application to listen on

**Source**: Auto-injected by Railway

**Default**: `8000` (in Dockerfile)

**Notes**:
- Railway manages port assignment
- Application should respect this value
- Our startup script uses fixed port 8000

---

### RAILWAY_ENVIRONMENT

**Description**: Railway deployment environment

**Source**: Auto-injected by Railway

**Values**: `production`, `staging`, `development`

**Notes**:
- Different from our ENVIRONMENT variable
- Used by Railway for deployment routing
- Can be used to determine deployment context

---

## AWS Configuration

### AWS_ACCESS_KEY_ID (Optional)

**Description**: AWS access key for service authentication

**Required**: Only if not using IAM role

**Format**: 20-character alphanumeric string

**Security**: Consider using IAM roles instead

**Example**:
```
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
```

**Notes**:
- Only needed if Railway doesn't support IAM roles
- Prefer IAM role-based authentication
- Rotate keys every 90 days

---

### AWS_SECRET_ACCESS_KEY (Optional)

**Description**: AWS secret key for service authentication

**Required**: Only if not using IAM role

**Format**: 40-character base64 string

**Security**: Store securely, never commit to git

**Example**:
```
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Notes**:
- Must be set alongside AWS_ACCESS_KEY_ID
- Rotate regularly for security
- Prefer IAM roles over access keys

---

## Authentication Configuration

### Complete Authentication Example

**AWS Cognito**:
```bash
OIDC_ISSUER_URL=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123
OIDC_CLIENT_ID=7abcdefghijklmnopqrstuv
JWT_TENANT_CLAIM_NAME=custom:tenant_id
JWT_MAX_LIFETIME_MINUTES=60
```

**Okta**:
```bash
OIDC_ISSUER_URL=https://your-domain.okta.com/oauth2/default
OIDC_CLIENT_ID=0oaabcdefghijklmno
JWT_TENANT_CLAIM_NAME=organization_id
JWT_MAX_LIFETIME_MINUTES=60
```

**Auth0**:
```bash
OIDC_ISSUER_URL=https://your-tenant.auth0.com/
OIDC_CLIENT_ID=abcdefghijklmnopqrstuvwxyz123456
JWT_TENANT_CLAIM_NAME=https://your-app.com/tenant_id
JWT_MAX_LIFETIME_MINUTES=60
```

---

## Application Configuration

### Complete Production Example

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO

# CORS
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com

# Database (auto-injected)
DATABASE_URL=postgresql://...

# Authentication
OIDC_ISSUER_URL=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123
OIDC_CLIENT_ID=7abcdefghijklmnopqrstuv
JWT_TENANT_CLAIM_NAME=tenant_id
JWT_MAX_LIFETIME_MINUTES=60

# AWS
AWS_REGION=us-east-1
AWS_SECRETS_MANAGER_SECRET_ID=hipaa-template/prod/secrets

# Optional tuning
JWKS_CACHE_TTL_SECONDS=3600
```

### Complete Development Example

```bash
# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/hipaa_db

# Authentication (mock or test IdP)
OIDC_ISSUER_URL=http://localhost:5000
OIDC_CLIENT_ID=test-client-id
JWT_TENANT_CLAIM_NAME=tenant_id
JWT_MAX_LIFETIME_MINUTES=120

# AWS (optional for local dev)
AWS_REGION=us-east-1
AWS_SECRETS_MANAGER_SECRET_ID=

# Optional tuning
JWKS_CACHE_TTL_SECONDS=600
```

---

## Sensitive Variables

These variables contain sensitive information and must be protected.

### In AWS Secrets Manager

**Secret ID**: Value from `AWS_SECRETS_MANAGER_SECRET_ID`

**Secret Contents** (JSON):
```json
{
  "OIDC_CLIENT_SECRET": "your-oauth-client-secret-here"
}
```

### Security Best Practices

1. **Never commit secrets to git**
   - Add `.env` to `.gitignore`
   - Use `.env.example` for documentation only

2. **Rotate secrets regularly**
   - OIDC_CLIENT_SECRET: Every 90 days
   - AWS access keys: Every 90 days
   - Database passwords: Every 90 days

3. **Use principle of least privilege**
   - Grant minimum required IAM permissions
   - Limit secret access to necessary services

4. **Audit secret access**
   - Enable CloudTrail for Secrets Manager
   - Monitor secret access logs
   - Alert on unusual access patterns

---

## Environment-Specific Examples

### Setting Variables via Railway CLI

```bash
# Set single variable
railway variables set ENVIRONMENT=production

# Set multiple variables
railway variables set \
  ENVIRONMENT=production \
  LOG_LEVEL=INFO \
  ALLOWED_ORIGINS=https://app.example.com

# Get variable
railway variables get ENVIRONMENT

# List all variables
railway variables list

# Delete variable
railway variables delete OLD_VARIABLE
```

### Setting Variables via Railway Dashboard

1. Open Railway project
2. Navigate to service
3. Click "Variables" tab
4. Click "+ New Variable"
5. Enter variable name and value
6. Click "Add"
7. Deploy triggers automatically

### Copying Variables Between Environments

```bash
# Export variables from staging
railway variables list --env staging > staging-vars.txt

# Set variables in production
railway variables set --env production $(cat staging-vars.txt)
```

---

## Verification

### Check All Required Variables Set

```bash
# List all variables
railway variables list

# Required variables checklist
railway variables get DATABASE_URL
railway variables get ENVIRONMENT
railway variables get ALLOWED_ORIGINS
railway variables get OIDC_ISSUER_URL
railway variables get OIDC_CLIENT_ID
railway variables get AWS_REGION
railway variables get AWS_SECRETS_MANAGER_SECRET_ID
```

### Test Application Configuration

```bash
# Test application starts successfully
railway logs --follow

# Check health endpoints
curl https://your-app.railway.app/api/v1/health/ready

# Verify logs show correct environment
railway logs | grep "ENVIRONMENT"

# Test authentication configuration
curl https://your-app.railway.app/api/v1/auth/validate \
  -H "Authorization: Bearer $TEST_TOKEN"
```

### Verify Secrets Manager Access

```bash
# Test AWS credentials
railway run aws sts get-caller-identity

# Test secret access
railway run aws secretsmanager get-secret-value \
  --secret-id hipaa-template/prod/secrets

# Check logs for secret loading
railway logs | grep "Secrets Manager"
```

---

## Troubleshooting

### Application Won't Start

1. Check all required variables are set
2. Verify DATABASE_URL is accessible
3. Check AWS credentials if using Secrets Manager
4. Review startup logs for errors

```bash
railway logs | grep -i "error"
```

### Authentication Fails

1. Verify OIDC_ISSUER_URL is accessible
2. Check JWKS endpoint: `{OIDC_ISSUER_URL}/.well-known/jwks.json`
3. Confirm OIDC_CLIENT_ID matches IdP
4. Verify JWT_TENANT_CLAIM_NAME matches token claims

```bash
# Test JWKS endpoint
curl $OIDC_ISSUER_URL/.well-known/jwks.json

# Decode JWT to check claims
jwt decode $TOKEN | jq .
```

### Secrets Manager Fails

1. Verify AWS_REGION is correct
2. Check IAM permissions for secret access
3. Confirm secret exists in specified region
4. Test secret access manually

```bash
# Check IAM identity
aws sts get-caller-identity

# Test secret access
aws secretsmanager get-secret-value \
  --secret-id $AWS_SECRETS_MANAGER_SECRET_ID \
  --region $AWS_REGION
```

---

## Additional Resources

- **Railway Documentation**: https://docs.railway.app/deploy/deployments
- **AWS Secrets Manager**: https://docs.aws.amazon.com/secretsmanager/
- **Environment Configuration**: See `.env.example` in repository
- **Authentication Setup**: See [AUTH_CONFIGURATION.md](AUTH_CONFIGURATION.md)
- **Deployment Guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)

---

## Summary

**Minimum Required Variables** for Railway Deployment:
```bash
# Auto-injected
DATABASE_URL=<auto-injected-by-railway>

# User-configured
ENVIRONMENT=production
ALLOWED_ORIGINS=https://app.example.com
OIDC_ISSUER_URL=https://your-idp.example.com
OIDC_CLIENT_ID=your_client_id
AWS_REGION=us-east-1
AWS_SECRETS_MANAGER_SECRET_ID=hipaa-template/prod/secrets
```

**AWS Secrets Manager** (sensitive):
```json
{
  "OIDC_CLIENT_SECRET": "your-client-secret"
}
```

For complete setup instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).
