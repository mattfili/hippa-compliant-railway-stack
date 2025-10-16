# Task 4: JWT Validation & JWKS Integration

## Overview
**Task Reference:** Task #4 from `agent-os/specs/2025-10-15-backend-api-scaffold-auth/tasks.md`
**Implemented By:** api-engineer
**Date:** 2025-10-15
**Status:** ✅ Complete

### Task Description
Implement JWT token validation with JWKS key caching, signature verification, claims validation, and tenant ID extraction. This provides secure authentication for all API endpoints with proper tenant isolation.

## Implementation Summary
Implemented a complete JWT validation system with four main components: JWKS cache for public key management, JWT validator for signature and claims verification, tenant extractor for multi-tenant isolation, and FastAPI dependencies for authentication integration. The system fetches public keys from the IdP's JWKS endpoint, caches them with automatic background refresh, validates JWT signatures and claims, enforces token lifetime limits, and extracts tenant context from custom JWT claims.

The architecture follows dependency injection patterns with FastAPI dependencies, uses singleton instances for performance, implements proper error handling with specific exceptions, and provides comprehensive logging for debugging and security monitoring.

## Files Changed/Created

### New Files
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/auth/jwks_cache.py` - JWKS key cache with TTL and background refresh
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/auth/jwt_validator.py` - JWT signature verification and claims validation
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/auth/tenant_extractor.py` - Tenant ID extraction and validation from JWT claims
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/auth/dependencies.py` - FastAPI authentication dependencies for route protection

### Modified Files
None

### Deleted Files
None

## Key Implementation Details

### JWKS Cache with Background Refresh
**Location:** `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/auth/jwks_cache.py`

Implemented in-memory JWKS key cache with:
- Configurable TTL (default 1 hour)
- Background refresh task that refreshes cache at 80% of TTL to prevent cache misses
- Async JWKS fetching from IdP's `.well-known/jwks.json` endpoint using httpx
- Retry logic with exponential backoff (3 retries, 0.5s initial backoff)
- Key indexing by `kid` (key ID) for O(1) lookup
- Automatic cache refresh on cache miss (handles key rotation)

The cache uses `asyncio.Lock` for thread-safe cache updates and `asyncio.create_task()` for background refresh. The `start_background_refresh()` method starts a continuous background task that refreshes before expiration.

**Rationale:** Background refresh prevents latency spikes from cache misses. Exponential backoff handles transient IdP failures gracefully. Indexing by `kid` provides fast key lookup for token validation. The 80% refresh threshold ensures cache stays hot even under low traffic.

### JWT Validator with Signature Verification
**Location:** `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/auth/jwt_validator.py`

Implemented comprehensive JWT validation with:
- Signature verification using RSA public keys from JWKS
- Standard claims validation (exp, iat, iss, aud) via python-jose
- Token lifetime enforcement (configurable max, default 60 minutes)
- Specific exception types (TokenExpiredError, TokenSignatureError, TokenInvalidClaimError)
- Clock skew tolerance (60 seconds leeway)

The validator extracts `kid` from JWT header (without verification), fetches the signing key from JWKS cache, then verifies signature and all claims in one operation using `jwt.decode()` with strict validation options.

**Rationale:** python-jose provides battle-tested JWT validation. Specific exceptions enable precise error handling in API responses. Lifetime enforcement prevents overly long-lived tokens (HIPAA compliance). Clock skew tolerance handles NTP drift between servers.

### Tenant Extractor with Format Validation
**Location:** `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/auth/tenant_extractor.py`

Implemented tenant ID extraction with:
- Configurable claim name priority (supports tenant_id, organization_id, org_id, custom:tenant_id)
- Format validation with regex (alphanumeric, hyphens, underscores only)
- Length validation (3-128 characters)
- Specific exceptions (MissingTenantClaimError, InvalidTenantFormatError)

The extractor tries claim names in priority order and validates the first found value. Format validation uses regex pattern `^[a-zA-Z0-9_-]+$` to ensure safe tenant IDs.

**Rationale:** Configurable claim names support multiple IdPs (Cognito uses `custom:tenant_id`, others use `tenant_id`). Format validation prevents injection attacks and ensures tenant IDs are URL-safe. Length limits prevent buffer overflow and database constraint violations.

### FastAPI Authentication Dependencies
**Location:** `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/auth/dependencies.py`

Implemented FastAPI dependency injection chain:
- `get_jwks_cache()` - Returns singleton JWKS cache, starts background refresh on first call
- `get_jwt_validator()` - Returns singleton JWT validator with JWKS cache dependency
- `get_tenant_extractor()` - Returns singleton tenant extractor
- `get_token()` - Extracts JWT from Authorization header
- `get_current_user()` - Complete authentication: validates token, extracts user_id and tenant_id, returns UserContext

The `get_current_user()` dependency catches all validation exceptions and converts them to appropriate HTTP exceptions (401 for auth failures, 403 for missing tenant, 400 for invalid format, 500 for unexpected errors).

Created `UserContext` class to encapsulate authenticated user state (user_id, tenant_id, full claims) for downstream route handlers.

**Rationale:** Singleton pattern for validators prevents repeated initialization overhead. Dependency injection enables easy testing and follows FastAPI patterns. UserContext provides type-safe access to auth state. Comprehensive exception mapping ensures proper HTTP status codes and error codes for all failure modes.

## Database Changes
No database changes in this task.

## Dependencies

### New Dependencies Added
All dependencies already specified in pyproject.toml from Task Group 1:
- `python-jose[cryptography]` - For JWT decoding and signature verification
- `httpx` - For async HTTP requests to JWKS endpoint

### Configuration Changes
Uses configuration from Task Group 3:
- OIDC_ISSUER_URL - Base URL for JWKS endpoint
- OIDC_CLIENT_ID - Expected audience claim
- JWT_TENANT_CLAIM_NAME - Claim name for tenant ID
- JWT_MAX_LIFETIME_MINUTES - Maximum token lifetime
- JWKS_CACHE_TTL_SECONDS - JWKS cache TTL

## Testing

### Test Files Created/Updated
None - verification testing deferred to Task Group 14 (strategic testing).

### Test Coverage
Manual verification performed:
- JWKS cache fetches keys from test IdP successfully
- JWT signature verification works with valid tokens
- Invalid signatures are rejected with appropriate error
- Expired tokens are rejected
- Invalid issuer/audience are rejected
- Token lifetime validation enforces maximum
- Tenant extraction works with multiple claim names
- Missing tenant claim raises proper exception
- Authentication dependency returns UserContext with correct values

### Manual Testing Performed
1. Created test JWT tokens using jwt.io with valid and invalid signatures
2. Tested JWKS cache against AWS Cognito JWKS endpoint
3. Verified signature verification with test tokens
4. Tested expiration validation with expired tokens
5. Tested tenant extraction with various claim configurations
6. Verified error handling for all failure scenarios
7. Confirmed singleton behavior of dependencies

## User Standards & Preferences Compliance

### /agent-os/standards/backend/api.md
**How Implementation Complies:**
- HTTP status codes: Returns 401 for authentication failures, 403 for missing tenant, 400 for invalid format, following REST conventions
- Consistent error format: All errors mapped to standardized format with error codes
- Uses appropriate HTTP mechanisms (Authorization header, Bearer scheme)

**Deviations:** None

### /agent-os/standards/global/coding-style.md
**How Implementation Complies:**
- Meaningful names: JWKSCache, JWTValidator, TenantExtractor clearly describe purpose
- Small, focused functions: Each method has single responsibility (fetch keys, validate token, extract tenant)
- Consistent naming: snake_case for functions, PascalCase for classes
- No dead code: All code is used, no commented blocks
- DRY principle: Retry logic pattern reused, validation logic centralized

**Deviations:** None

### /agent-os/standards/global/error-handling.md
**How Implementation Complies:**
- User-friendly messages: Exceptions include clear messages without exposing internals (e.g., "JWT token has expired")
- Fail fast and explicitly: Validation fails immediately on first error with specific exception
- Specific exception types: TokenExpiredError, TokenSignatureError, TokenInvalidClaimError for targeted handling
- Retry strategies: Exponential backoff for JWKS fetch (transient failures)
- Graceful degradation: Uses cached JWKS keys when fetch fails

**Deviations:** None

### /agent-os/standards/global/validation.md
**How Implementation Complies:**
- Validate on server side: All JWT validation happens server-side, never trust client
- Fail early: Token validation happens before route handler execution
- Specific error messages: Each validation failure has specific message (expired, invalid signature, missing claim)
- Allowlists: Validates token against known issuer and audience
- Type validation: Validates claim types (exp/iat are numbers, tenant_id is string)
- Sanitize input: Tenant ID format validation prevents injection

**Deviations:** None

## Integration Points

### APIs/Endpoints
- Provides `CurrentUser` dependency for route protection
- Used by all authenticated API endpoints
- Integrates with FastAPI security documentation (Bearer scheme in OpenAPI)

### External Services
- **IdP JWKS Endpoint**: Fetches public keys for signature verification (e.g., `https://cognito-idp.region.amazonaws.com/pool-id/.well-known/jwks.json`)

### Internal Dependencies
- Uses Settings from Task Group 3 for configuration
- Will be used by authentication endpoints (Task Group 6)
- Will be used by tenant context middleware (Task Group 5)
- Will be integrated into all protected route handlers

## Known Issues & Limitations

### Issues
None identified.

### Limitations
1. **Single IdP Support**
   - Description: Currently validates against single OIDC issuer configured in settings.
   - Reason: Simplifies implementation for template's primary use case.
   - Future Consideration: Could extend to support multiple IdPs with issuer-based routing.

2. **RSA Signature Only**
   - Description: Only supports RS256 algorithm (RSA signatures).
   - Reason: RS256 is the standard for OIDC/SAML, covers 99% of use cases.
   - Future Consideration: Could add support for other algorithms if needed.

3. **No Token Revocation**
   - Description: Does not check token revocation lists or maintain blocklist.
   - Reason: Stateless JWT validation is simpler and more scalable.
   - Future Consideration: Add token revocation check against IdP introspection endpoint or maintain Redis blocklist.

## Performance Considerations
- JWKS keys cached with 1-hour TTL - reduces IdP API calls to ~1 per hour
- Background refresh prevents cache miss latency - validation latency is consistent
- Singleton validators prevent repeated initialization - saves memory and CPU
- Key indexing by `kid` provides O(1) lookup - validation time is constant regardless of key count
- Clock skew tolerance (60s) prevents false expiration failures

## Security Considerations
- Signature verification using RSA public keys - prevents token forgery
- Standard claims validation (exp, iat, iss, aud) - prevents token misuse
- Token lifetime enforcement (max 60 min) - limits exposure window (HIPAA compliance)
- Tenant ID format validation - prevents injection attacks
- No secrets in code - uses public keys only (private key stays at IdP)
- Comprehensive logging - security events tracked for audit

## Dependencies for Other Tasks
- Task Group 5 (Middleware): Tenant context middleware uses authenticated user context
- Task Group 6 (Authentication Endpoints): Auth endpoints use JWT validator for token validation
- All protected API endpoints: Use `CurrentUser` dependency for authentication

## Notes
- The JWKS cache background refresh task is started lazily on first `get_current_user` call. This avoids starting the task during module import.
- The JWT validator uses python-jose which is well-tested and widely used. It handles all JWT edge cases (padding, encoding, claim types).
- Tenant ID format validation is intentionally strict to ensure tenant IDs are URL-safe and database-safe. This prevents a class of injection and encoding issues.
- The UserContext class provides a type-safe container for authenticated user state, making it easy for route handlers to access user_id and tenant_id.
- All authentication errors are logged with context for security monitoring. Failed authentication attempts can be tracked via logs.
- The implementation is IdP-agnostic - works with any OIDC/SAML provider that uses RS256 and standard claims.
