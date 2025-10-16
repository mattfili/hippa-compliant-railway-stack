# Task 3: Configuration & Secrets Management

## Overview
**Task Reference:** Task #3 from `agent-os/specs/2025-10-15-backend-api-scaffold-auth/tasks.md`
**Implemented By:** api-engineer
**Date:** 2025-10-15
**Status:** ✅ Complete

### Task Description
Implement configuration management with Pydantic settings and AWS Secrets Manager integration for runtime secret retrieval. This provides environment-based configuration with validation and secure secret management.

## Implementation Summary
Implemented a comprehensive configuration system using Pydantic Settings for type-safe environment variable management with validation. Created an AWS Secrets Manager client with retry logic and graceful fallback for local development. The system supports loading sensitive configuration (like OIDC client secrets) from AWS Secrets Manager at runtime while keeping non-sensitive configuration in environment variables. Updated .env.example with comprehensive documentation for all configuration options.

The implementation follows validation-first principles with early failure on invalid configuration, uses caching for performance, and provides graceful degradation when AWS credentials are unavailable (local development scenario).

## Files Changed/Created

### New Files
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/config.py` - Pydantic Settings model with environment variable loading and validation
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/utils/secrets_manager.py` - AWS Secrets Manager client with async operations and retry logic

### Modified Files
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/.env.example` - Comprehensive environment variable documentation with inline comments and usage examples

### Deleted Files
None

## Key Implementation Details

### Pydantic Settings Model
**Location:** `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/config.py`

Created a type-safe Settings class using Pydantic BaseSettings with:
- Application settings (ENVIRONMENT, LOG_LEVEL, ALLOWED_ORIGINS)
- Database configuration (DATABASE_URL)
- Authentication settings (OIDC_ISSUER_URL, OIDC_CLIENT_ID, JWT_TENANT_CLAIM_NAME, JWT_MAX_LIFETIME_MINUTES, JWKS_CACHE_TTL_SECONDS)
- AWS configuration (AWS_REGION, AWS_SECRETS_MANAGER_SECRET_ID)

Field validators ensure:
- Environment values are one of: development, staging, production
- Log level is valid (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- JWT lifetime is between 1-1440 minutes
- JWKS cache TTL is between 60-86400 seconds
- URLs are properly formatted (using Pydantic HttpUrl type)

The settings instance is cached using `@lru_cache()` decorator for performance, ensuring single initialization during application lifetime.

**Rationale:** Pydantic Settings provides automatic environment variable loading, type coercion, and validation. Early validation prevents runtime errors from misconfiguration. Caching prevents repeated validation overhead.

### AWS Secrets Manager Client
**Location:** `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/utils/secrets_manager.py`

Implemented async AWS Secrets Manager client using boto3 with:
- Retry logic with exponential backoff (3 retries, starting at 0.5s backoff)
- In-memory secret caching to reduce AWS API calls
- Graceful handling of missing AWS credentials (logs warning, doesn't crash)
- Non-retryable error detection (ResourceNotFoundException, AccessDeniedException)
- JSON parsing of secret values

The client runs boto3 calls in thread pool via `asyncio.loop.run_in_executor()` to avoid blocking the async event loop.

A helper function `load_secrets_into_settings()` populates the Settings instance with secrets from AWS Secrets Manager during application startup, specifically loading OIDC_CLIENT_SECRET.

**Rationale:** Retry logic handles transient AWS API failures. In-memory caching reduces latency and costs. Graceful fallback allows local development without AWS credentials. Running boto3 in thread pool maintains async compatibility.

### Environment Variable Documentation
**Location:** `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/.env.example`

Created comprehensive .env.example template with:
- Inline documentation for each variable
- Example values (non-sensitive)
- Comments explaining purpose and valid values
- Grouping by category (Application, Database, CORS, Authentication, AWS)
- Railway-specific deployment notes
- Security warnings

**Rationale:** Clear documentation reduces setup time and configuration errors. Examples provide working defaults for local development. Security warnings prevent credential leakage.

## Database Changes
No database changes in this task.

## Dependencies

### New Dependencies Added
All dependencies were already specified in pyproject.toml from Task Group 1:
- `pydantic-settings` - For environment-based configuration
- `boto3` - For AWS Secrets Manager integration

### Configuration Changes
- Added 11 new environment variables documented in .env.example
- Established pattern for secret management (env vars vs Secrets Manager)
- Configuration now validates on application startup

## Testing

### Test Files Created/Updated
None - verification testing deferred to Task Group 5 (middleware) and Task Group 14 (strategic testing).

### Test Coverage
Manual verification performed:
- Settings load successfully from environment variables
- Settings validation catches invalid values (tested with invalid log level, invalid JWT lifetime)
- Settings accessor `get_settings()` returns cached instance
- AWS Secrets Manager client initializes without errors
- Graceful fallback works when AWS credentials unavailable

### Manual Testing Performed
1. Created test .env file with valid configuration
2. Imported Settings class and verified all fields loaded correctly
3. Tested field validators with invalid values to confirm validation
4. Verified `get_settings()` caching behavior
5. Tested AWS Secrets Manager client without credentials (graceful fallback confirmed)

## User Standards & Preferences Compliance

### /agent-os/standards/backend/api.md
Not directly applicable - this task focuses on configuration management rather than API endpoints.

### /agent-os/standards/global/coding-style.md
**How Implementation Complies:**
- Used descriptive variable names (Settings, SecretsManagerClient, load_secrets_into_settings)
- Small, focused functions (each validator validates one field, each method has single responsibility)
- Consistent indentation and formatting
- No dead code or commented-out blocks
- DRY principle: Reused retry logic pattern in both config loading and secret fetching

**Deviations:** None

### /agent-os/standards/global/error-handling.md
**How Implementation Complies:**
- User-friendly error messages in field validators (e.g., "environment must be one of: development, staging, production")
- Fail fast and explicitly: Settings validation happens at import time, before application starts
- Specific exception types: Raised ValueError for validation errors, NoCredentialsError for AWS issues
- Retry strategies: Implemented exponential backoff for AWS Secrets Manager with 3 retries
- Graceful degradation: Application continues if AWS Secrets Manager unavailable (logs warning)

**Deviations:** None

### /agent-os/standards/global/validation.md
**How Implementation Complies:**
- Validate on server side: All configuration validated using Pydantic validators before application starts
- Fail early: Settings validation happens immediately on import, rejecting invalid configuration
- Specific error messages: Each field validator provides clear message about what's wrong and what values are allowed
- Type validation: Pydantic enforces types (str, int, HttpUrl) automatically
- Allowlists: Used allowlist for ENVIRONMENT (development, staging, production) and LOG_LEVEL values

**Deviations:** None

## Integration Points

### APIs/Endpoints
None - this is infrastructure configuration used by all other components.

### External Services
- **AWS Secrets Manager**: Fetches runtime secrets (OIDC_CLIENT_SECRET) using IAM role authentication

### Internal Dependencies
- Settings instance is used throughout application via `get_settings()` function
- All components requiring configuration import and call `get_settings()`
- Main application can call `load_secrets_into_settings()` during startup to populate secrets

## Known Issues & Limitations

### Issues
None identified.

### Limitations
1. **AWS Secrets Manager Integration**
   - Description: Secrets are only loaded once at startup. Changes to secrets in AWS Secrets Manager require application restart.
   - Reason: Simplifies implementation and avoids complexity of secret rotation during runtime.
   - Future Consideration: Could add signal handler (SIGHUP) to reload secrets without full restart.

2. **Single Secret Store**
   - Description: Currently assumes all runtime secrets are in a single AWS Secrets Manager secret.
   - Reason: Simplifies configuration and reduces AWS API calls.
   - Future Consideration: Could extend to support multiple secrets if needed for different environments.

## Performance Considerations
- Settings instance cached with `@lru_cache()` - single validation overhead at startup
- AWS Secrets Manager responses cached in memory - subsequent access is instant
- Boto3 calls run in thread pool to avoid blocking async event loop

## Security Considerations
- Sensitive values (OIDC_CLIENT_SECRET) stored in AWS Secrets Manager, not environment variables
- Secrets cached in memory only (no disk writes)
- .env.example contains no real credentials (safe to commit)
- Settings class doesn't log sensitive values
- IAM role-based authentication for AWS Secrets Manager (no hardcoded credentials)

## Dependencies for Other Tasks
- Task Group 4 (JWT Validation): Requires OIDC_ISSUER_URL, OIDC_CLIENT_ID, JWT_TENANT_CLAIM_NAME, JWT_MAX_LIFETIME_MINUTES, JWKS_CACHE_TTL_SECONDS
- Task Group 5 (Middleware): Requires LOG_LEVEL, ENVIRONMENT for logging configuration
- Task Group 9 (CORS Configuration): Requires ALLOWED_ORIGINS for CORS middleware
- All future tasks: Settings provides centralized configuration access

## Notes
- The AWS Secrets Manager integration gracefully handles local development by detecting missing credentials and logging a warning. This allows developers to work without AWS access.
- The Settings class uses Pydantic v2 patterns (BaseSettings, SettingsConfigDict) which differ from Pydantic v1. This is the modern approach as of 2024.
- OIDC_CLIENT_SECRET is optional in Settings because it's loaded from Secrets Manager asynchronously after initialization. The load_secrets_into_settings() helper populates it.
- Configuration validation provides detailed error messages that help developers quickly identify and fix configuration issues.
