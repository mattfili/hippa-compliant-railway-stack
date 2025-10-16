# Error Code Registry

This document provides a comprehensive list of all error codes used in the HIPAA-compliant backend API, including descriptions, HTTP status codes, common causes, and resolution strategies.

## Table of Contents

- [Error Response Format](#error-response-format)
- [Authentication Errors (AUTH_001 - AUTH_999)](#authentication-errors-auth_001---auth_999)
- [System Errors (SYS_001 - SYS_999)](#system-errors-sys_001---sys_999)
- [Validation Errors (VAL_001 - VAL_999)](#validation-errors-val_001---val_999)
- [Adding New Error Codes](#adding-new-error-codes)
- [Error Handling Best Practices](#error-handling-best-practices)
- [Troubleshooting Guide](#troubleshooting-guide)

## Error Response Format

All API errors follow this standardized JSON format:

```json
{
  "error": {
    "code": "AUTH_001",
    "message": "Invalid authentication token",
    "detail": "Token signature verification failed",
    "request_id": "req-123-abc-456"
  }
}
```

### Response Fields

| Field | Type | Description | Always Present? |
|-------|------|-------------|-----------------|
| `code` | string | Error code identifier | Yes |
| `message` | string | User-friendly error message | Yes |
| `detail` | string | Technical detail for debugging | Development only |
| `request_id` | string | Request ID for log correlation | Yes |

### HTTP Status Codes

Errors return appropriate HTTP status codes:

- **400 Bad Request**: Invalid input, validation errors
- **401 Unauthorized**: Authentication failures (invalid/expired token)
- **403 Forbidden**: Authorization failures (missing permissions, tenant access)
- **404 Not Found**: Resource not found (future feature)
- **500 Internal Server Error**: Unexpected application errors
- **503 Service Unavailable**: External dependency failures (database, secrets manager)

## Authentication Errors (AUTH_001 - AUTH_999)

### AUTH_001: Invalid Token

**Description**: The provided JWT token is invalid or malformed.

**HTTP Status**: 401 Unauthorized

**Message**: "Invalid authentication token"

**Common Causes**:
- Token signature verification failed
- Token format is malformed (not a valid JWT)
- JWKS endpoint returned unexpected key format
- Token was tampered with

**Example Response**:
```json
{
  "error": {
    "code": "AUTH_001",
    "message": "Invalid authentication token",
    "request_id": "req-789-def-012"
  }
}
```

**Resolution**:
1. Verify token is correctly formatted JWT (3 base64 parts separated by dots)
2. Check IdP JWKS endpoint is accessible
3. Confirm token was issued by configured IdP (check `iss` claim)
4. Verify token hasn't been modified

**Prevention**:
- Always obtain tokens directly from IdP (never construct manually)
- Use HTTPS for all token transmission
- Validate tokens immediately upon receipt

---

### AUTH_002: CSRF Validation Failed

**Description**: CSRF token validation failed during authentication callback.

**HTTP Status**: 403 Forbidden

**Message**: "CSRF token validation failed"

**Common Causes**:
- State parameter doesn't match session
- Replay attack detected
- Cookie-based session expired
- Cross-site request attempted

**Example Response**:
```json
{
  "error": {
    "code": "AUTH_002",
    "message": "CSRF token validation failed",
    "request_id": "req-456-ghi-789"
  }
}
```

**Resolution**:
1. Verify state parameter sent in authorization request
2. Check cookies are enabled in browser
3. Ensure request originates from same domain
4. Verify session hasn't expired

**Prevention**:
- Always include state parameter in OAuth flows
- Use secure, httpOnly cookies for state storage
- Implement short session timeouts

---

### AUTH_003: Token Expired

**Description**: The JWT token has expired and is no longer valid.

**HTTP Status**: 401 Unauthorized

**Message**: "Authentication token has expired"

**Common Causes**:
- Token expiration time (`exp` claim) in the past
- Token lifetime exceeded maximum allowed (60 minutes)
- Clock skew between client and server
- Token cached on client side

**Example Response**:
```json
{
  "error": {
    "code": "AUTH_003",
    "message": "Authentication token has expired",
    "request_id": "req-123-jkl-456"
  }
}
```

**Resolution**:
1. Obtain new token from IdP
2. Check system clock synchronization (use NTP)
3. Verify token `exp` claim: `jwt decode $TOKEN | jq .exp`
4. Clear cached tokens

**Prevention**:
- Implement token refresh before expiration
- Set appropriate token lifetimes (60 minutes for HIPAA)
- Synchronize server clocks with NTP
- Don't cache tokens beyond expiration time

---

### AUTH_004: Invalid Token Signature

**Description**: The token signature verification failed using IdP's public key.

**HTTP Status**: 401 Unauthorized

**Message**: "Invalid token signature"

**Common Causes**:
- Token signed with different key than expected
- JWKS key rotation occurred
- Man-in-the-middle attack
- Token altered in transit

**Example Response**:
```json
{
  "error": {
    "code": "AUTH_004",
    "message": "Invalid token signature",
    "request_id": "req-789-mno-012"
  }
}
```

**Resolution**:
1. Verify JWKS endpoint accessible: `curl https://idp.example.com/.well-known/jwks.json`
2. Check token header `kid` matches JWKS key: `jwt decode $TOKEN | jq .header.kid`
3. Restart application to refresh JWKS cache
4. Verify IdP configuration matches OIDC_ISSUER_URL

**Prevention**:
- Use HTTPS for all IdP communication
- Implement JWKS cache with reasonable TTL (1 hour)
- Handle key rotation gracefully (fetch new keys on verification failure)

---

### AUTH_005: Missing Tenant Claim

**Description**: The JWT token is missing the required tenant claim.

**HTTP Status**: 403 Forbidden

**Message**: "Missing tenant claim in JWT token"

**Common Causes**:
- IdP not configured to include custom tenant claim
- Lambda/hook function not adding tenant_id
- User missing tenant_id attribute
- Wrong JWT_TENANT_CLAIM_NAME configured

**Example Response**:
```json
{
  "error": {
    "code": "AUTH_005",
    "message": "Missing tenant claim in JWT token",
    "request_id": "req-456-pqr-789"
  }
}
```

**Resolution**:
1. Decode JWT and check for tenant claim: `jwt decode $TOKEN | jq .payload`
2. Verify IdP custom claim configuration
3. Check Lambda/hook function logs for errors
4. Verify JWT_TENANT_CLAIM_NAME environment variable
5. Ensure user has tenant_id attribute set

**Prevention**:
- Test JWT structure during IdP setup
- Add user tenant_id validation in user creation flow
- Monitor Lambda/hook execution for errors
- Document tenant claim requirements for onboarding

---

### AUTH_006: Invalid Redirect URI

**Description**: The provided redirect URI is not in the allowed list.

**HTTP Status**: 400 Bad Request

**Message**: "Invalid redirect URI"

**Common Causes**:
- Redirect URI not registered in IdP
- URI doesn't match ALLOWED_ORIGINS
- Protocol mismatch (http vs https)
- Domain mismatch

**Example Response**:
```json
{
  "error": {
    "code": "AUTH_006",
    "message": "Invalid redirect URI",
    "request_id": "req-123-stu-456"
  }
}
```

**Resolution**:
1. Verify redirect URI in IdP allowed list
2. Check ALLOWED_ORIGINS environment variable
3. Ensure exact match (including trailing slash)
4. Use HTTPS in production

**Prevention**:
- Register all valid redirect URIs in IdP
- Use environment variables for redirect URIs
- Document required URIs for different environments

## System Errors (SYS_001 - SYS_999)

### SYS_001: Database Unreachable

**Description**: The application cannot connect to the PostgreSQL database.

**HTTP Status**: 503 Service Unavailable

**Message**: "Database connection unavailable"

**Common Causes**:
- Database service down
- Network connectivity issues
- Connection pool exhausted
- Invalid DATABASE_URL
- Database credentials invalid

**Example Response**:
```json
{
  "error": {
    "code": "SYS_001",
    "message": "Database connection unavailable",
    "request_id": "req-789-vwx-012"
  }
}
```

**Resolution**:
1. Check database service status in Railway dashboard
2. Verify DATABASE_URL environment variable
3. Test connection: `psql $DATABASE_URL -c "SELECT 1"`
4. Check application logs for connection errors
5. Restart application to reset connection pool

**Prevention**:
- Monitor database health metrics
- Configure connection pooling (pool_size=10, max_overflow=10)
- Implement connection retry logic with exponential backoff
- Set up database replication for high availability

---

### SYS_002: Secrets Manager Unavailable

**Description**: AWS Secrets Manager is unreachable or returned an error.

**HTTP Status**: 503 Service Unavailable

**Message**: "Secrets Manager unavailable"

**Common Causes**:
- AWS Secrets Manager service outage
- IAM permissions insufficient
- Secret doesn't exist
- Network connectivity to AWS
- Wrong AWS region configured

**Example Response**:
```json
{
  "error": {
    "code": "SYS_002",
    "message": "Secrets Manager unavailable",
    "request_id": "req-456-yzab-789"
  }
}
```

**Resolution**:
1. Verify AWS Secrets Manager service status
2. Check IAM role has `secretsmanager:GetSecretValue` permission
3. Verify secret exists: `aws secretsmanager describe-secret --secret-id <id>`
4. Check AWS_REGION environment variable
5. Test AWS credentials: `aws sts get-caller-identity`

**Prevention**:
- Grant least-privilege IAM permissions
- Monitor AWS service health
- Implement secret caching with reasonable TTL
- Set up CloudWatch alarms for secret access failures

---

### SYS_003: Internal Server Error

**Description**: An unexpected error occurred in the application.

**HTTP Status**: 500 Internal Server Error

**Message**: "An unexpected error occurred"

**Common Causes**:
- Unhandled exception in application code
- Out of memory
- Missing environment variables
- Code bug (null pointer, division by zero, etc.)

**Example Response**:
```json
{
  "error": {
    "code": "SYS_003",
    "message": "An unexpected error occurred",
    "request_id": "req-123-cdef-456"
  }
}
```

**Resolution**:
1. Check application logs for stack trace
2. Correlate error using request_id
3. Verify all required environment variables set
4. Restart application if memory issue
5. Report bug if reproducible

**Prevention**:
- Comprehensive error handling in all routes
- Input validation before processing
- Monitor memory usage and set appropriate limits
- Implement graceful degradation for non-critical failures

## Validation Errors (VAL_001 - VAL_999)

### VAL_001: Invalid Input

**Description**: The provided input data is invalid.

**HTTP Status**: 400 Bad Request

**Message**: "Invalid input data provided"

**Common Causes**:
- Wrong data type
- Value out of range
- Invalid format
- Failed Pydantic validation

**Example Response**:
```json
{
  "error": {
    "code": "VAL_001",
    "message": "Invalid input data provided",
    "request_id": "req-789-ghij-012"
  }
}
```

**Resolution**:
- Check API documentation for expected input format
- Validate data types and ranges
- Review Pydantic model schema

---

### VAL_002: Missing Field

**Description**: A required field is missing from the request.

**HTTP Status**: 400 Bad Request

**Message**: "Required field is missing"

**Common Causes**:
- Required field omitted from request body
- Field name misspelled
- Field sent as null instead of omitted

**Example Response**:
```json
{
  "error": {
    "code": "VAL_002",
    "message": "Required field is missing",
    "request_id": "req-456-klmn-789"
  }
}
```

**Resolution**:
- Check API documentation for required fields
- Verify field names match schema exactly
- Include all required fields in request

---

### VAL_003: Invalid Format

**Description**: The data format is invalid (e.g., date format, email format).

**HTTP Status**: 400 Bad Request

**Message**: "Invalid data format"

**Common Causes**:
- Invalid email format
- Wrong date/time format
- Invalid UUID format
- Malformed JSON

**Example Response**:
```json
{
  "error": {
    "code": "VAL_003",
    "message": "Invalid data format",
    "request_id": "req-123-opqr-456"
  }
}
```

**Resolution**:
- Check expected format in API documentation
- Validate formats client-side before sending
- Use standard formats (ISO 8601 for dates, RFC 5322 for emails)

## Adding New Error Codes

To add new error codes for custom domains (e.g., documents, users):

### Step 1: Add to ErrorCode Enum

Edit `backend/app/utils/errors.py`:

```python
class ErrorCode(str, Enum):
    # ... existing codes ...

    # Document Errors (DOC_001 - DOC_999)
    DOC_NOT_FOUND = "DOC_001"  # Document not found
    DOC_INVALID_FORMAT = "DOC_002"  # Invalid document format
    DOC_SIZE_EXCEEDED = "DOC_003"  # Document size exceeds limit
    DOC_UPLOAD_FAILED = "DOC_004"  # Document upload failed
```

### Step 2: Add Descriptions

```python
ERROR_DESCRIPTIONS: Dict[str, str] = {
    # ... existing descriptions ...

    # Document Errors
    ErrorCode.DOC_NOT_FOUND: "Document not found",
    ErrorCode.DOC_INVALID_FORMAT: "Invalid document format",
    ErrorCode.DOC_SIZE_EXCEEDED: "Document size exceeds limit",
    ErrorCode.DOC_UPLOAD_FAILED: "Document upload failed",
}
```

### Step 3: Add Status Code Mappings

```python
ERROR_STATUS_CODES: Dict[str, int] = {
    # ... existing mappings ...

    # Document Errors
    ErrorCode.DOC_NOT_FOUND: 404,
    ErrorCode.DOC_INVALID_FORMAT: 400,
    ErrorCode.DOC_SIZE_EXCEEDED: 413,
    ErrorCode.DOC_UPLOAD_FAILED: 500,
}
```

### Step 4: Create Custom Exception Class

```python
class DocumentError(APIException):
    """Exception for document-related errors."""

    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            detail=detail,
            status_code=status_code,
        )
```

### Step 5: Document in This File

Add new section following the format above with:
- Error code and name
- Description
- HTTP status
- Common causes
- Example response
- Resolution steps
- Prevention strategies

### Step 6: Use in Application Code

```python
from app.utils.errors import ErrorCode, DocumentError

@router.get("/{document_id}")
async def get_document(document_id: str):
    document = await db.get(Document, document_id)
    if not document:
        raise DocumentError(
            error_code=ErrorCode.DOC_NOT_FOUND,
            message=f"Document {document_id} not found",
            detail=f"No document with ID {document_id} in tenant scope",
        )
    return {"document": document.to_dict()}
```

## Error Handling Best Practices

### For Backend Developers

1. **Use Appropriate Error Codes**: Choose the most specific error code that matches the failure condition

2. **Provide Helpful Messages**: User-facing messages should be actionable and clear

3. **Include Technical Details**: Add detail field for debugging (filtered in production)

4. **Log Full Context**: Log complete error with stack trace and request context

5. **Never Expose Sensitive Data**: Don't include PHI, tokens, or secrets in errors

6. **Handle Errors at Boundaries**: Catch exceptions at API layer, not scattered throughout code

7. **Return Consistent Format**: Always use `format_error_response` for errors

### For Frontend Developers

1. **Check Status Codes**: Use HTTP status codes for error categorization

2. **Display Error Messages**: Show `error.message` to users

3. **Log Error Codes**: Log `error.code` and `error.request_id` for support

4. **Implement Retry Logic**: Retry on 503 errors with exponential backoff

5. **Handle 401/403 Specially**: Redirect to login on authentication failures

6. **Correlate with Logs**: Include `request_id` when reporting issues

## Troubleshooting Guide

### General Debugging Process

1. **Identify Error Code**: Note the exact error code from response
2. **Find Request ID**: Get `request_id` from error response
3. **Check Logs**: Search logs for request_id to see full context
4. **Review Documentation**: Check this document for error code details
5. **Follow Resolution Steps**: Apply suggested resolutions
6. **Verify Fix**: Test that error no longer occurs

### Common Error Patterns

| Error Pattern | Likely Cause | First Step |
|---------------|--------------|------------|
| All requests failing with AUTH_001 | JWKS endpoint issue | Check IdP availability |
| Intermittent AUTH_003 errors | Clock skew | Synchronize server clocks |
| AUTH_005 on specific users | Missing tenant attribute | Check user profile in IdP |
| SYS_001 after deployment | Database migration failed | Check migration logs |
| SYS_002 on startup | IAM permissions | Verify IAM role attached |

### Log Correlation

Use request_id to correlate errors with server logs:

```bash
# Search logs for request_id
grep "req-123-abc-456" /var/log/application.log

# Railway logs
railway logs | grep "req-123-abc-456"

# CloudWatch Insights query
fields @timestamp, @message
| filter request_id = "req-123-abc-456"
| sort @timestamp desc
```

### Testing Error Responses

Test error handling with invalid requests:

```bash
# Test expired token
curl -X GET http://localhost:8000/api/v1/auth/validate \
  -H "Authorization: Bearer expired_token"

# Test missing tenant claim
curl -X GET http://localhost:8000/api/v1/auth/validate \
  -H "Authorization: Bearer token_without_tenant"

# Test invalid input
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}'
```

## Additional Resources

- **API Architecture**: See [API_ARCHITECTURE.md](API_ARCHITECTURE.md) for error handling patterns
- **Authentication**: See [AUTH_CONFIGURATION.md](AUTH_CONFIGURATION.md) for auth error troubleshooting
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md) for production error monitoring
- **HIPAA Compliance**: See [HIPAA_READINESS.md](HIPAA_READINESS.md) for audit logging requirements

## Support

If you encounter errors not documented here:

1. Check application logs for detailed error message
2. Search project issues for similar errors
3. Create new issue with:
   - Error code
   - Request ID
   - Steps to reproduce
   - Relevant log excerpts
