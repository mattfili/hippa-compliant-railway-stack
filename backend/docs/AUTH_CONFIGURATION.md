# Authentication Configuration Guide

This guide explains how to configure identity providers (IdPs) for JWT-based authentication with the HIPAA-compliant backend API.

## Table of Contents

- [Overview](#overview)
- [JWT Token Structure](#jwt-token-structure)
- [AWS Cognito Setup](#aws-cognito-setup)
- [Generic OIDC Configuration](#generic-oidc-configuration)
- [Other Identity Providers](#other-identity-providers)
- [Token Expiration Recommendations](#token-expiration-recommendations)
- [Testing Authentication Locally](#testing-authentication-locally)
- [Troubleshooting](#troubleshooting)

## Overview

The backend API uses JWT (JSON Web Token) authentication with OIDC/SAML identity providers. The authentication flow:

1. **User Authentication**: User logs in via IdP (AWS Cognito, Okta, Auth0, Azure AD)
2. **Token Issuance**: IdP issues JWT token with custom tenant claim
3. **Token Validation**: Backend validates JWT signature using JWKS endpoint
4. **Tenant Extraction**: Backend extracts tenant_id from JWT custom claim
5. **Request Authorization**: Backend uses tenant context for data isolation

### Key Requirements

All identity providers must support:

- **OIDC or SAML 2.0** authentication flows
- **JWT tokens** with RS256 signature algorithm
- **JWKS endpoint** for public key distribution
- **Custom claims** for tenant_id injection
- **Multi-Factor Authentication** (MFA) capability
- **Business Associate Agreement** (BAA) for HIPAA compliance

## JWT Token Structure

### Required Standard Claims

```json
{
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123",
  "sub": "user-uuid-1234-5678",
  "aud": "your-client-id",
  "exp": 1698765432,
  "iat": 1698761832,
  "token_use": "id"
}
```

**Standard Claims Explained**:
- `iss` (issuer): IdP's unique identifier URL
- `sub` (subject): Unique user identifier
- `aud` (audience): Application client ID
- `exp` (expiration): Unix timestamp when token expires
- `iat` (issued at): Unix timestamp when token was issued
- `token_use`: Token type (id, access, or refresh)

### Required Custom Claims

The backend requires a custom claim for tenant identification:

```json
{
  "tenant_id": "org-uuid-9876-5432",
  "email": "user@example.com",
  "name": "John Doe"
}
```

**Custom Claim Options** (configurable via `JWT_TENANT_CLAIM_NAME`):
- `tenant_id` (recommended)
- `organization_id`
- `org_id`
- `custom:tenant_id` (AWS Cognito format)

### Complete JWT Example

```json
{
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123",
  "sub": "user-uuid-1234-5678",
  "aud": "7abcdefghijklmn",
  "exp": 1698765432,
  "iat": 1698761832,
  "token_use": "id",
  "tenant_id": "org-uuid-9876-5432",
  "email": "user@example.com",
  "email_verified": true,
  "cognito:username": "johndoe",
  "name": "John Doe"
}
```

## AWS Cognito Setup

Step-by-step guide to configure AWS Cognito as your identity provider.

### Prerequisites

- AWS account with BAA signed
- AWS CLI installed and configured
- Administrative access to AWS Console

### Step 1: Create User Pool

```bash
# Create user pool with MFA enabled
aws cognito-idp create-user-pool \
  --pool-name hipaa-compliant-app \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 12,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": true
    }
  }' \
  --mfa-configuration REQUIRED \
  --user-attribute-update-settings '{
    "AttributesRequireVerificationBeforeUpdate": ["email"]
  }' \
  --auto-verified-attributes email \
  --schema '[
    {
      "Name": "email",
      "AttributeDataType": "String",
      "Required": true,
      "Mutable": true
    },
    {
      "Name": "tenant_id",
      "AttributeDataType": "String",
      "Mutable": true
    }
  ]'
```

**Or via AWS Console**:

1. Navigate to AWS Cognito → User Pools → Create user pool
2. **Authentication providers**: Cognito user pool
3. **Password policy**: Strong password requirements (12+ chars, mixed case, numbers, symbols)
4. **MFA enforcement**: Required (TOTP or SMS)
5. **User attributes**: Email (required), custom attribute `tenant_id`
6. **Email verification**: Required
7. **Message templates**: Customize invite and verification emails

### Step 2: Create App Client

```bash
# Create app client for your application
aws cognito-idp create-user-pool-client \
  --user-pool-id us-east-1_ABC123 \
  --client-name backend-api-client \
  --generate-secret \
  --allowed-o-auth-flows code \
  --allowed-o-auth-scopes openid email profile \
  --allowed-o-auth-flows-user-pool-client \
  --callback-urls https://your-app.railway.app/api/v1/auth/callback \
  --logout-urls https://your-app.railway.app \
  --supported-identity-providers COGNITO
```

**Or via AWS Console**:

1. User Pool → App clients → Create app client
2. **Client type**: Confidential client (with client secret)
3. **Authentication flows**: Authorization code grant
4. **OAuth 2.0 scopes**: openid, email, profile
5. **Callback URLs**: `https://your-app.railway.app/api/v1/auth/callback`
6. **Sign-out URLs**: `https://your-app.railway.app`
7. Save the **Client ID** and **Client Secret**

### Step 3: Configure Hosted UI

```bash
# Configure hosted UI domain
aws cognito-idp create-user-pool-domain \
  --domain hipaa-app-prod \
  --user-pool-id us-east-1_ABC123
```

**Or via AWS Console**:

1. User Pool → App integration → Domain
2. **Domain prefix**: `hipaa-app-prod` (creates `hipaa-app-prod.auth.us-east-1.amazoncognito.com`)
3. Or use custom domain with SSL certificate

### Step 4: Add Custom Tenant Claim

AWS Cognito doesn't automatically add custom attributes to JWT tokens. Use a Pre Token Generation Lambda trigger:

```python
# lambda_function.py
import json


def lambda_handler(event, context):
    """
    Pre Token Generation trigger to inject tenant_id claim.

    This Lambda is invoked before JWT token generation and adds
    the tenant_id custom attribute as a claim in the token.
    """
    # Get user attributes
    user_attributes = event['request']['userAttributes']

    # Extract tenant_id from custom attribute
    tenant_id = user_attributes.get('custom:tenant_id')

    if tenant_id:
        # Add tenant_id to ID token claims
        event['response']['claimsOverrideDetails'] = {
            'claimsToAddOrOverride': {
                'tenant_id': tenant_id
            }
        }
    else:
        # Log warning if tenant_id missing
        print(f"WARNING: User {user_attributes.get('email')} missing tenant_id")

    return event
```

**Deploy Lambda**:

```bash
# Create Lambda function
aws lambda create-function \
  --function-name cognito-add-tenant-claim \
  --runtime python3.11 \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --zip-file fileb://lambda.zip

# Grant Cognito permission to invoke Lambda
aws lambda add-permission \
  --function-name cognito-add-tenant-claim \
  --statement-id cognito-trigger \
  --action lambda:InvokeFunction \
  --principal cognito-idp.amazonaws.com \
  --source-arn arn:aws:cognito-idp:us-east-1:ACCOUNT_ID:userpool/us-east-1_ABC123

# Attach Lambda trigger to user pool
aws cognito-idp update-user-pool \
  --user-pool-id us-east-1_ABC123 \
  --lambda-config '{
    "PreTokenGeneration": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:cognito-add-tenant-claim"
  }'
```

### Step 5: Configure Environment Variables

Update your Railway environment or `.env` file:

```bash
OIDC_ISSUER_URL=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123
OIDC_CLIENT_ID=7abcdefghijklmn
JWT_TENANT_CLAIM_NAME=tenant_id
JWT_MAX_LIFETIME_MINUTES=60
```

Store the client secret in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name hipaa-template/prod/secrets \
  --secret-string '{"OIDC_CLIENT_SECRET":"your-client-secret-here"}' \
  --region us-east-1
```

### Step 6: Create Test Users

```bash
# Create user with tenant_id
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_ABC123 \
  --username johndoe@example.com \
  --user-attributes \
    Name=email,Value=johndoe@example.com \
    Name=custom:tenant_id,Value=org-uuid-9876-5432 \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_ABC123 \
  --username johndoe@example.com \
  --password 'TempPassword123!' \
  --permanent
```

### Step 7: Test Authentication

1. Navigate to Cognito Hosted UI: `https://hipaa-app-prod.auth.us-east-1.amazoncognito.com/login`
2. Log in with test user credentials
3. Complete MFA setup (TOTP authenticator app)
4. After successful login, you'll be redirected to callback URL with auth code
5. Backend exchanges auth code for JWT token
6. Verify JWT contains `tenant_id` claim

## Generic OIDC Configuration

For other OIDC-compliant providers (Okta, Auth0, Azure AD):

### Required OIDC Endpoints

Your IdP must expose these endpoints:

```bash
# Discovery endpoint (provides URLs for other endpoints)
GET https://your-idp.example.com/.well-known/openid-configuration

# JWKS endpoint (public keys for signature verification)
GET https://your-idp.example.com/.well-known/jwks.json

# Authorization endpoint (user login)
GET https://your-idp.example.com/oauth2/authorize

# Token endpoint (exchange auth code for JWT)
POST https://your-idp.example.com/oauth2/token

# Logout endpoint (invalidate session)
GET https://your-idp.example.com/oauth2/logout
```

### Configuration Parameters

```bash
# Backend environment variables
OIDC_ISSUER_URL=https://your-idp.example.com
OIDC_CLIENT_ID=your-application-client-id
JWT_TENANT_CLAIM_NAME=organization_id  # or custom claim name
JWT_MAX_LIFETIME_MINUTES=60

# AWS Secrets Manager (OIDC_CLIENT_SECRET)
{
  "OIDC_CLIENT_SECRET": "your-client-secret"
}
```

### Custom Claim Injection

Most IdPs support custom claims via:

**Option 1: Custom Attributes**
- Add custom user attribute (e.g., `tenant_id`, `organization_id`)
- Configure IdP to include attribute in JWT tokens

**Option 2: Lambda/Hook Functions**
- Okta: Token Inline Hooks
- Auth0: Rules or Actions
- Azure AD: Claims mapping policy

**Option 3: Group Mapping**
- Map user groups to tenant_id claim
- Use IdP group management for tenant assignment

## Other Identity Providers

### Okta

**Setup Steps**:
1. Create Okta OIDC application (Authorization Code flow)
2. Add custom user profile attribute: `tenantId`
3. Create Token Inline Hook to inject `tenant_id` claim
4. Configure callback URLs and allowed CORS origins
5. Enable MFA in Okta security settings

**Environment Variables**:
```bash
OIDC_ISSUER_URL=https://your-domain.okta.com/oauth2/default
OIDC_CLIENT_ID=your-okta-client-id
JWT_TENANT_CLAIM_NAME=tenant_id
```

**Token Inline Hook** (Node.js):
```javascript
module.exports = async (context) => {
  const user = context.data.identity;
  return {
    commands: [{
      type: 'com.okta.identity.patch',
      value: [{
        op: 'add',
        path: '/claims/tenant_id',
        value: user.profile.tenantId
      }]
    }]
  };
};
```

### Auth0

**Setup Steps**:
1. Create Auth0 Regular Web Application
2. Add custom user metadata field: `tenant_id`
3. Create Rule to add `tenant_id` to token
4. Configure callback URLs and allowed web origins
5. Enable MFA in Auth0 security settings

**Environment Variables**:
```bash
OIDC_ISSUER_URL=https://your-tenant.auth0.com/
OIDC_CLIENT_ID=your-auth0-client-id
JWT_TENANT_CLAIM_NAME=tenant_id
```

**Auth0 Rule**:
```javascript
function addTenantClaim(user, context, callback) {
  const namespace = 'https://your-app.com/';
  const tenantId = user.user_metadata.tenant_id;

  if (tenantId) {
    context.idToken[namespace + 'tenant_id'] = tenantId;
    context.accessToken[namespace + 'tenant_id'] = tenantId;
  }

  callback(null, user, context);
}
```

### Azure AD (Microsoft Entra ID)

**Setup Steps**:
1. Register application in Azure AD
2. Add custom extension attribute: `extension_tenant_id`
3. Create claims mapping policy
4. Configure redirect URIs
5. Enable MFA via Conditional Access

**Environment Variables**:
```bash
OIDC_ISSUER_URL=https://login.microsoftonline.com/{tenant-id}/v2.0
OIDC_CLIENT_ID=your-azure-ad-client-id
JWT_TENANT_CLAIM_NAME=tenant_id
```

**Claims Mapping Policy** (PowerShell):
```powershell
$policy = @{
  ClaimsMappingPolicy = @{
    Version = 1
    IncludeBasicClaimSet = "true"
    ClaimsSchema = @(
      @{
        Source = "user"
        ID = "extensionattribute1"
        JwtClaimType = "tenant_id"
      }
    )
  }
}

New-AzureADPolicy -Definition $policy -DisplayName "TenantClaimPolicy"
```

## Token Expiration Recommendations

### HIPAA Compliance Guidelines

For applications handling Protected Health Information (PHI):

**Recommended Token Lifetimes**:
- **Access Token**: 60 minutes maximum
- **Refresh Token**: 24 hours (with rotation)
- **Session**: 60 minutes with idle timeout

**Configuration**:
```bash
JWT_MAX_LIFETIME_MINUTES=60
```

### Token Lifetime Trade-offs

| Lifetime | Security | User Experience | Recommendation |
|----------|----------|-----------------|----------------|
| 15 min   | Highest  | Poor (frequent re-auth) | High-security clinical apps |
| 60 min   | High     | Good balance | **Recommended** for most use cases |
| 4 hours  | Medium   | Best | Administrative apps only |
| 24 hours | Low      | Excellent | **Not recommended** for PHI access |

### Token Validation

The backend validates:

1. **Signature**: JWT signed by IdP's private key
2. **Expiration**: `exp` claim not in the past
3. **Lifetime**: `(exp - iat) <= JWT_MAX_LIFETIME_MINUTES`
4. **Issuer**: `iss` matches `OIDC_ISSUER_URL`
5. **Audience**: `aud` matches `OIDC_CLIENT_ID`
6. **Tenant Claim**: `tenant_id` (or configured claim) present

## Testing Authentication Locally

### Mock JWT Tokens

For local development without IdP, create mock JWT tokens:

```python
# mock_token.py
import jwt
import datetime

# Mock JWKS key pair (for testing only!)
PRIVATE_KEY = """
-----BEGIN RSA PRIVATE KEY-----
[Your test private key]
-----END RSA PRIVATE KEY-----
"""

PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
[Your test public key]
-----END PUBLIC KEY-----
"""

# Generate mock JWT
payload = {
    "iss": "https://mock-idp.example.com",
    "sub": "test-user-123",
    "aud": "test-client-id",
    "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
    "iat": datetime.datetime.now(datetime.UTC),
    "tenant_id": "test-tenant-123",
    "email": "test@example.com",
    "name": "Test User"
}

token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
print(f"Mock JWT: {token}")
```

### Local JWKS Server

Run mock JWKS endpoint for testing:

```python
# mock_jwks.py
from flask import Flask, jsonify
import json

app = Flask(__name__)

JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "use": "sig",
            "kid": "test-key-id",
            "n": "your-public-key-modulus",
            "e": "AQAB"
        }
    ]
}

@app.route("/.well-known/jwks.json")
def jwks():
    return jsonify(JWKS)

if __name__ == "__main__":
    app.run(port=5000)
```

Update `.env` for local testing:
```bash
OIDC_ISSUER_URL=http://localhost:5000
OIDC_CLIENT_ID=test-client-id
JWT_TENANT_CLAIM_NAME=tenant_id
```

### cURL Testing

Test authentication endpoints with mock tokens:

```bash
# Test token validation
curl -X GET http://localhost:8000/api/v1/auth/validate \
  -H "Authorization: Bearer ${MOCK_JWT_TOKEN}"

# Expected response
{
  "valid": true,
  "user_id": "test-user-123",
  "tenant_id": "test-tenant-123",
  "expires_at": 1698765432
}
```

## Troubleshooting

### JWT Validation Fails

**Error**: `AUTH_001: Invalid token signature`

**Causes**:
- JWKS endpoint unreachable
- Wrong public key used for validation
- Token signed with different key than advertised

**Solutions**:
```bash
# Verify JWKS endpoint accessible
curl https://your-idp.example.com/.well-known/jwks.json

# Check logs for JWKS fetch errors
docker logs backend-api | grep "JWKS"

# Verify token header kid matches JWKS key
jwt decode $TOKEN | jq .header.kid
```

### Tenant Claim Missing

**Error**: `AUTH_005: Missing tenant claim in JWT`

**Causes**:
- IdP not configured to include custom claim
- Lambda/hook function not deployed
- User missing `tenant_id` attribute

**Solutions**:
```bash
# Verify JWT contains tenant_id
jwt decode $TOKEN | jq .payload.tenant_id

# Check IdP claim configuration
# AWS Cognito: Lambda trigger logs
# Okta: Token Inline Hook logs
# Auth0: Rule execution logs

# Update JWT_TENANT_CLAIM_NAME if using different claim
export JWT_TENANT_CLAIM_NAME=organization_id
```

### Token Expired

**Error**: `AUTH_003: Token expired`

**Causes**:
- Token lifetime exceeded
- Clock skew between systems
- Token cached on client side

**Solutions**:
```bash
# Check token expiration
jwt decode $TOKEN | jq '.payload | {iat, exp, now: now}'

# Verify system clocks synchronized (NTP)
timedatectl status

# Reduce token lifetime in IdP
JWT_MAX_LIFETIME_MINUTES=60
```

### JWKS Cache Issues

**Error**: `Failed to fetch JWKS keys`

**Causes**:
- Network connectivity to IdP
- IdP rate limiting
- JWKS cache stale after key rotation

**Solutions**:
```bash
# Check JWKS endpoint connectivity
curl -v https://your-idp.example.com/.well-known/jwks.json

# Restart application to refresh cache
railway service restart

# Adjust cache TTL
JWKS_CACHE_TTL_SECONDS=1800  # 30 minutes
```

## Security Best Practices

1. **Always Use HTTPS**: Never transmit JWT tokens over HTTP
2. **Short Token Lifetimes**: 60 minutes or less for PHI access
3. **Validate All Claims**: Signature, expiration, issuer, audience
4. **Secure Client Secret**: Store in AWS Secrets Manager, never in code
5. **Enable MFA**: Required for all users with PHI access
6. **Rotate Keys**: Regular key rotation in IdP (every 90 days)
7. **Monitor Token Usage**: Log all authentication events
8. **BAA Required**: Ensure IdP has signed Business Associate Agreement

## Next Steps

After configuring authentication:

1. Review [ERROR_CODES.md](ERROR_CODES.md) for authentication error codes
2. See [API_ARCHITECTURE.md](API_ARCHITECTURE.md) for using auth dependencies
3. Check [HIPAA_READINESS.md](HIPAA_READINESS.md) for compliance requirements
4. Follow [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
