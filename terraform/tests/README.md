# Terraform Tests

## Overview

This directory contains Terratest-based tests for validating Terraform infrastructure modules. Tests are written in Go and use the Terratest framework to provision real AWS resources, verify their configuration, and clean up after testing.

## Test Structure

- `unit/` - Unit tests for individual modules
  - `kms_test.go` - KMS module tests (8 tests)
  - `s3_test.go` - S3 module tests (8 tests)
  - Additional module tests as they are developed

## Prerequisites

- Go 1.21 or higher
- AWS account with appropriate permissions
- AWS credentials configured (via environment variables or ~/.aws/credentials)
- Terraform >= 1.5.0 installed

## Running Tests

### Run All Unit Tests

```bash
cd /terraform/tests
go test -v -timeout 30m ./unit/...
```

### Run Specific Module Tests

```bash
# KMS module tests
cd /terraform/tests
go test -v -timeout 30m ./unit/kms_test.go

# S3 module tests
cd /terraform/tests
go test -v -timeout 30m ./unit/s3_test.go
```

### Run a Specific Test

```bash
cd /terraform/tests
go test -v -timeout 30m ./unit/kms_test.go -run TestKMSKeyCreation
```

### Run Tests in Parallel

All tests are configured to run in parallel using `t.Parallel()` for faster execution:

```bash
cd /terraform/tests
go test -v -timeout 30m -parallel 4 ./unit/...
```

## KMS Module Tests

The KMS module includes 8 focused tests:

1. **TestKMSKeyCreation** - Verifies KMS master key and outputs are created
2. **TestKMSKeyRotationEnabled** - Verifies automatic key rotation is enabled
3. **TestKMSKeyRotationDisabled** - Verifies key rotation can be disabled
4. **TestKMSKeyAlias** - Validates key alias naming format
5. **TestKMSKeyPolicy** - Verifies key policy configuration with account ID
6. **TestKMSMultipleEnvironments** - Tests dev/staging/production deployments
7. **TestKMSKeyTags** - Validates custom tag application
8. **TestKMSInvalidEnvironment** - Tests input validation for environment variable

## S3 Module Tests

The S3 module includes 8 focused tests:

1. **TestS3ModuleBucketCreation** - Verifies all three buckets are created with correct naming convention
2. **TestS3ModuleEncryption** - Verifies SSE-KMS encryption is enabled on all buckets
3. **TestS3ModuleVersioning** - Verifies versioning is enabled on all buckets
4. **TestS3ModulePublicAccessBlock** - Verifies public access is blocked on all buckets (HIPAA requirement)
5. **TestS3ModuleLifecyclePolicies** - Verifies lifecycle policies are configured when enabled
6. **TestS3ModuleOutputs** - Verifies all module outputs are populated correctly
7. **TestS3ModuleAccessLogging** - Verifies access logging is configured to audit bucket

## Test Execution Time

- Individual test: 2-5 minutes (includes resource creation and cleanup)
- Full KMS test suite (parallel): 5-10 minutes
- Full S3 test suite (parallel): 5-10 minutes
- Sequential execution: 20-30 minutes per module

## AWS Resource Cleanup

All tests use `defer terraform.Destroy(t, terraformOptions)` to ensure resources are cleaned up even if tests fail. However, if a test is interrupted (Ctrl+C), resources may remain in AWS and need manual cleanup.

### Manual Cleanup Commands

```bash
# List KMS keys
aws kms list-keys --region us-east-1

# Schedule KMS key deletion
aws kms schedule-key-deletion --key-id <key-id> --pending-window-in-days 7

# List S3 buckets
aws s3 ls | grep hipaa-compliant

# Delete S3 bucket (must be empty)
aws s3 rb s3://bucket-name --force
```

## Cost Considerations

Running tests provisions real AWS resources and incurs costs:

- KMS keys: $1/month per key (prorated, ~$0.03 per test run)
- S3 buckets: Minimal cost (storage is empty during tests)
- KMS operations: ~$0.03 per test run
- Data transfer: Negligible

**Estimated cost per full test run**: Less than $0.10

## Debugging Failed Tests

### View Terraform Output

Set `TERRATEST_LOG_PARSER` environment variable:

```bash
export TERRATEST_LOG_PARSER=true
go test -v -timeout 30m ./unit/kms_test.go
```

### Preserve Resources for Debugging

Comment out the `defer terraform.Destroy` line in the test to keep resources for manual inspection.

### Check AWS Console

If tests fail, check the AWS Console:
- KMS keys with naming pattern `hipaa-master-key-test`
- S3 buckets with naming pattern `hipaa-compliant-*-test-*`
- CloudFormation stacks (if using Terraform backend)

## CI/CD Integration

These tests can be integrated into GitHub Actions or other CI/CD pipelines:

```yaml
- name: Run Terraform Tests
  run: |
    cd terraform/tests
    go test -v -timeout 30m ./unit/...
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    AWS_DEFAULT_REGION: us-east-1
```

## Test Coverage Goals

- **Unit Tests**: 2-8 focused tests per module
- **Integration Tests**: End-to-end tests in `integration/` directory
- **Total Expected**: 30-70 tests maximum across all modules

## Future Enhancements

- Integration tests for full stack deployment
- Performance tests for large-scale deployments
- Security scanning integration (tfsec, checkov)
- Cost estimation validation tests
